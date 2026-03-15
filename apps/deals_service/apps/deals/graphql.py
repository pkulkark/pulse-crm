import json
from urllib import error, request

from ariadne import EnumType, MutationType, ObjectType, QueryType, gql
from ariadne.contrib.federation import FederatedObjectType, make_federated_schema
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from graphql import GraphQLError

from .events import emit_deal_status_changed_event
from .models import Deal, DealStatus


type_defs = gql(
    """
    enum DealStatus {
      NEW
      QUALIFIED
      WON
      LOST
    }

    type Deal @key(fields: "id") {
      id: ID!
      companyId: ID!
      primaryContactId: ID
      status: DealStatus!
      company: Company!
      primaryContact: Contact
    }

    type Company @key(fields: "id") {
      id: ID!
    }

    type Contact @key(fields: "id") {
      id: ID!
    }

    input CreateDealInput {
      companyId: ID!
      primaryContactId: ID
      status: DealStatus!
    }

    input UpdateDealStatusInput {
      dealId: ID!
      status: DealStatus!
    }

    extend type Query {
      deals: [Deal!]!
      deal(id: ID!): Deal
    }

    type Mutation {
      createDeal(input: CreateDealInput!): Deal!
      updateDealStatus(input: UpdateDealStatusInput!): Deal!
    }
    """
)

ALLOWED_STATUS_TRANSITIONS = {
    DealStatus.NEW: {
        DealStatus.NEW,
        DealStatus.QUALIFIED,
        DealStatus.WON,
        DealStatus.LOST,
    },
    DealStatus.QUALIFIED: {
        DealStatus.QUALIFIED,
        DealStatus.WON,
        DealStatus.LOST,
    },
    DealStatus.WON: {DealStatus.WON},
    DealStatus.LOST: {DealStatus.LOST},
}

query = QueryType()
mutation = MutationType()
deal = FederatedObjectType("Deal")
deal_status = EnumType(
    "DealStatus",
    {
        "NEW": DealStatus.NEW,
        "QUALIFIED": DealStatus.QUALIFIED,
        "WON": DealStatus.WON,
        "LOST": DealStatus.LOST,
    },
)


def get_request_user(info):
    return info.context["request_context"]["user"]


def require_authenticated_user(info):
    user = get_request_user(info)

    if not user["id"]:
        raise GraphQLError(
            "Authentication is required.",
            extensions={"code": "UNAUTHENTICATED"},
        )

    return user


def get_visible_deals(info) -> QuerySet[Deal]:
    user = require_authenticated_user(info)
    queryset = Deal.objects.all()

    if user["role"] == "admin":
        return queryset

    if not user["companyId"]:
        return queryset.none()

    return queryset.filter(company_id=user["companyId"])


def normalize_optional_text(value):
    if value is None:
        return None

    stripped_value = value.strip()
    return stripped_value or None


def normalize_required_id(value, field_name):
    normalized_value = normalize_optional_text(value)

    if normalized_value is None:
        raise GraphQLError(
            f"{field_name} is required.",
            extensions={"code": "BAD_USER_INPUT"},
        )

    return normalized_value


def raise_validation_error(error):
    messages = []

    if hasattr(error, "message_dict"):
        for field_errors in error.message_dict.values():
            messages.extend(field_errors)
    else:
        messages.extend(error.messages)

    raise GraphQLError(
        " ".join(messages),
        extensions={"code": "BAD_USER_INPUT"},
    ) from error


def require_company_scope(info, company_id):
    user = require_authenticated_user(info)

    if user["role"] == "admin":
        return user

    if not user["companyId"] or str(company_id) != user["companyId"]:
        raise GraphQLError(
            "You do not have access to this company.",
            extensions={"code": "FORBIDDEN"},
        )

    return user


def build_crm_graphql_request_context(info):
    request_context = info.context["request_context"]
    headers = {
        "Content-Type": "application/json",
        "X-Correlation-Id": request_context["correlationId"],
        "X-User-Role": request_context["user"]["role"],
    }

    if request_context["user"]["id"]:
        headers["X-User-Id"] = request_context["user"]["id"]

    if request_context["user"]["companyId"]:
        headers["X-Company-Id"] = request_context["user"]["companyId"]

    return headers


def execute_crm_query(info, query_text, variables):
    payload = json.dumps(
        {
            "query": query_text,
            "variables": variables,
        }
    ).encode("utf-8")
    graphql_request = request.Request(
        settings.CRM_RELATIONSHIPS_GRAPHQL_URL,
        data=payload,
        headers=build_crm_graphql_request_context(info),
        method="POST",
    )

    try:
        with request.urlopen(
            graphql_request,
            timeout=settings.CRM_RELATIONSHIPS_GRAPHQL_TIMEOUT_SECONDS,
        ) as response:
            response_payload = json.load(response)
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GraphQLError(
            "Company and contact validation is unavailable.",
            extensions={"code": "INTERNAL_SERVER_ERROR"},
        ) from exc

    if response_payload.get("errors"):
        raise GraphQLError(
            "Company and contact validation failed.",
            extensions={"code": "INTERNAL_SERVER_ERROR"},
        )

    return response_payload.get("data", {})


def fetch_reference_records(info, company_id, primary_contact_id):
    if primary_contact_id is None:
        return execute_crm_query(
            info,
            """
            query ValidateDealCompany($companyId: ID!) {
              company(id: $companyId) {
                id
              }
            }
            """,
            {"companyId": str(company_id)},
        )

    return execute_crm_query(
        info,
        """
        query ValidateDealReferences($companyId: ID!, $primaryContactId: ID!) {
          company(id: $companyId) {
            id
          }
          contact(id: $primaryContactId) {
            id
            companyId
          }
        }
        """,
        {
            "companyId": str(company_id),
            "primaryContactId": str(primary_contact_id),
        },
    )


def validate_references(info, company_id, primary_contact_id):
    references = fetch_reference_records(info, company_id, primary_contact_id)

    if references.get("company") is None:
        raise GraphQLError(
            "Company not found.",
            extensions={"code": "BAD_USER_INPUT"},
        )

    if primary_contact_id is None:
        return

    contact = references.get("contact")

    if contact is None:
        raise GraphQLError(
            "Primary contact not found.",
            extensions={"code": "BAD_USER_INPUT"},
        )

    if contact["companyId"] != str(company_id):
        raise GraphQLError(
            "Primary contact must belong to the selected company.",
            extensions={"code": "BAD_USER_INPUT"},
        )


def save_deal(instance):
    try:
        instance.full_clean()
    except ValidationError as validation_error:
        raise_validation_error(validation_error)

    instance.save()
    return instance


def get_visible_deal_or_error(info, deal_id):
    try:
        return get_visible_deals(info).get(id=deal_id)
    except (Deal.DoesNotExist, ValidationError, ValueError) as exc:
        raise GraphQLError(
            "Deal not found.",
            extensions={"code": "BAD_USER_INPUT"},
        ) from exc


def validate_status_transition(current_status, next_status):
    allowed_statuses = ALLOWED_STATUS_TRANSITIONS[DealStatus(current_status)]

    if DealStatus(next_status) in allowed_statuses:
        return

    raise GraphQLError(
        f"Cannot change deal status from {current_status} to {next_status}.",
        extensions={"code": "BAD_USER_INPUT"},
    )


@query.field("deals")
def resolve_deals(_, info):
    return get_visible_deals(info)


@query.field("deal")
def resolve_deal(_, info, id):
    try:
        return get_visible_deals(info).filter(id=id).first()
    except (ValidationError, ValueError):
        return None


@mutation.field("createDeal")
def resolve_create_deal(_, info, input):
    company_id = normalize_required_id(input["companyId"], "Company")
    primary_contact_id = normalize_optional_text(input.get("primaryContactId"))
    status = input["status"]

    require_company_scope(info, company_id)
    validate_references(info, company_id, primary_contact_id)

    instance = Deal(
        company_id=company_id,
        primary_contact_id=primary_contact_id,
        status=status,
    )
    return save_deal(instance)


@mutation.field("updateDealStatus")
def resolve_update_deal_status(_, info, input):
    deal_id = normalize_required_id(input["dealId"], "Deal")
    next_status = input["status"]
    instance = get_visible_deal_or_error(info, deal_id)

    validate_status_transition(instance.status, next_status)

    if instance.status == next_status:
        return instance

    old_status = instance.status
    request_context = info.context["request_context"]

    with transaction.atomic():
        instance.status = next_status
        updated_instance = save_deal(instance)
        transaction.on_commit(
            lambda: emit_deal_status_changed_event(
                deal=updated_instance,
                old_status=old_status,
                new_status=next_status,
                correlation_id=request_context["correlationId"],
            )
        )

    return updated_instance


@deal.field("companyId")
def resolve_deal_company_id(obj, _info):
    return str(obj.company_id)


@deal.field("primaryContactId")
def resolve_deal_primary_contact_id(obj, _info):
    return str(obj.primary_contact_id) if obj.primary_contact_id else None


@deal.field("company")
def resolve_deal_company(obj, _info):
    return {"id": str(obj.company_id)}


@deal.field("primaryContact")
def resolve_deal_primary_contact(obj, _info):
    if obj.primary_contact_id is None:
        return None

    return {"id": str(obj.primary_contact_id)}


@deal.reference_resolver
def resolve_deal_reference(_, _info, representation):
    return Deal.objects.filter(id=representation["id"]).first()


schema = make_federated_schema(type_defs, [query, mutation, deal, deal_status])
