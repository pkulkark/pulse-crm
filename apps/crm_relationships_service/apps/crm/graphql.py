from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from graphql import GraphQLError

from ariadne import MutationType, QueryType, gql
from ariadne.contrib.federation import FederatedObjectType, make_federated_schema

from .models import Company, Contact


type_defs = gql(
    """
    type Company @key(fields: "id") {
      id: ID!
      name: String!
      parentCompanyId: ID
      parentCompany: Company
      childCompanies: [Company!]!
      contacts: [Contact!]!
    }

    type Contact @key(fields: "id") {
      id: ID!
      companyId: ID!
      company: Company!
      name: String!
      email: String!
      jobTitle: String
    }

    input CreateCompanyInput {
      name: String!
      parentCompanyId: ID
    }

    input UpdateCompanyInput {
      companyId: ID!
      name: String!
      parentCompanyId: ID
    }

    input CreateContactInput {
      companyId: ID!
      name: String!
      email: String!
      jobTitle: String
    }

    input UpdateContactInput {
      contactId: ID!
      name: String!
      email: String!
      jobTitle: String
    }

    extend type Query {
      companies: [Company!]!
      company(id: ID!): Company
      contact(id: ID!): Contact
    }

    type Mutation {
      createCompany(input: CreateCompanyInput!): Company!
      updateCompany(input: UpdateCompanyInput!): Company!
      createContact(input: CreateContactInput!): Contact!
      updateContact(input: UpdateContactInput!): Contact!
    }
    """
)

query = QueryType()
mutation = MutationType()
company = FederatedObjectType("Company")
contact = FederatedObjectType("Contact")


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


def require_admin_user(info):
    user = require_authenticated_user(info)

    if user["role"] != "admin":
        raise GraphQLError(
            "Only admins can modify companies and contacts.",
            extensions={"code": "FORBIDDEN"},
        )

    return user


def get_visible_companies(info) -> QuerySet[Company]:
    user = require_authenticated_user(info)
    queryset = Company.objects.select_related("parent_company").all()

    if user["role"] == "admin":
        return queryset

    if not user["companyId"]:
        return queryset.none()

    return queryset.filter(id=user["companyId"])


def is_company_visible(info, company_id):
    return get_visible_companies(info).filter(id=company_id).exists()


def normalize_optional_text(value):
    if value is None:
        return None

    stripped_value = value.strip()
    return stripped_value or None


def normalize_required_text(value, field_name):
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


def get_company_or_error(company_id, message):
    try:
        return Company.objects.select_related("parent_company").get(id=company_id)
    except (Company.DoesNotExist, ValidationError, ValueError) as error:
        raise GraphQLError(
            message,
            extensions={"code": "BAD_USER_INPUT"},
        ) from error


def get_contact_or_error(contact_id, message):
    try:
        return Contact.objects.select_related("company").get(id=contact_id)
    except (Contact.DoesNotExist, ValidationError, ValueError) as error:
        raise GraphQLError(
            message,
            extensions={"code": "BAD_USER_INPUT"},
        ) from error


def apply_company_updates(instance, input_data):
    instance.name = normalize_required_text(input_data["name"], "Company name")

    parent_company_id = normalize_optional_text(input_data.get("parentCompanyId"))
    if parent_company_id is None:
        instance.parent_company = None
        return

    instance.parent_company = get_company_or_error(
        parent_company_id,
        "Parent company not found.",
    )


def save_company(instance):
    try:
        instance.full_clean()
    except ValidationError as error:
        raise_validation_error(error)

    instance.save()
    return instance


def apply_contact_updates(instance, input_data):
    instance.name = normalize_required_text(input_data["name"], "Contact name")
    instance.email = normalize_required_text(input_data["email"], "Email").lower()
    instance.job_title = normalize_optional_text(input_data.get("jobTitle", ""))


def save_contact(instance):
    try:
        instance.full_clean()
    except ValidationError as error:
        raise_validation_error(error)

    instance.save()
    return instance


@query.field("companies")
def resolve_companies(_, info):
    return get_visible_companies(info).order_by("name", "id")


@query.field("company")
def resolve_company(_, info, id):
    try:
        return get_visible_companies(info).filter(id=id).first()
    except (ValidationError, ValueError):
        return None


@query.field("contact")
def resolve_contact(_, info, id):
    visible_companies = get_visible_companies(info).values("id")
    try:
        return (
            Contact.objects.select_related("company")
            .filter(id=id, company_id__in=visible_companies)
            .first()
        )
    except (ValidationError, ValueError):
        return None


@mutation.field("createCompany")
def resolve_create_company(_, info, input):
    require_admin_user(info)

    instance = Company()
    apply_company_updates(instance, input)
    return save_company(instance)


@mutation.field("updateCompany")
def resolve_update_company(_, info, input):
    require_admin_user(info)

    instance = get_company_or_error(input["companyId"], "Company not found.")
    apply_company_updates(instance, input)
    return save_company(instance)


@mutation.field("createContact")
def resolve_create_contact(_, info, input):
    require_admin_user(info)

    instance = Contact(
        company=get_company_or_error(input["companyId"], "Company not found."),
    )
    apply_contact_updates(instance, input)
    return save_contact(instance)


@mutation.field("updateContact")
def resolve_update_contact(_, info, input):
    require_admin_user(info)

    instance = get_contact_or_error(input["contactId"], "Contact not found.")
    apply_contact_updates(instance, input)
    return save_contact(instance)


@company.field("parentCompanyId")
def resolve_company_parent_company_id(obj, _info):
    return str(obj.parent_company_id) if obj.parent_company_id else None


@company.field("parentCompany")
def resolve_company_parent_company(obj, info):
    if obj.parent_company_id is None or not is_company_visible(
        info,
        obj.parent_company_id,
    ):
        return None

    return obj.parent_company


@company.field("childCompanies")
def resolve_company_child_companies(obj, info):
    visible_companies = get_visible_companies(info).values("id")
    return obj.child_companies.filter(id__in=visible_companies).order_by("name", "id")


@company.field("contacts")
def resolve_company_contacts(obj, _info):
    return obj.contacts.all().order_by("name", "id")


@company.reference_resolver
def resolve_company_reference(_, _info, representation):
    return Company.objects.filter(id=representation["id"]).first()


@contact.field("companyId")
def resolve_contact_company_id(obj, _info):
    return str(obj.company_id)


@contact.field("company")
def resolve_contact_company(obj, _info):
    return obj.company


@contact.field("jobTitle")
def resolve_contact_job_title(obj, _info):
    return obj.job_title or None


@contact.reference_resolver
def resolve_contact_reference(_, _info, representation):
    return Contact.objects.select_related("company").filter(
        id=representation["id"],
    ).first()


schema = make_federated_schema(type_defs, [query, mutation, company, contact])
