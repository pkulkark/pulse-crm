import json
from datetime import date, datetime, timezone
from urllib import error, request

from ariadne import (
    EnumType,
    MutationType,
    ObjectType,
    QueryType,
    gql,
)
from ariadne.contrib.federation import FederatedObjectType, make_federated_schema
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from graphql import GraphQLError

from .models import Activity, ActivityType, Company, Contact, Task, TaskPriority, TaskStatus


type_defs = gql(
    """
    enum TaskStatus {
      OPEN
      COMPLETED
    }

    enum TaskPriority {
      LOW
      MEDIUM
      HIGH
    }

    enum ActivityType {
      CALL
      EMAIL
      MEETING
      NOTE
    }

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

    type Deal @key(fields: "id") {
      id: ID!
    }

    type Task {
      id: ID!
      title: String!
      companyId: ID!
      contactId: ID
      dealId: ID
      userId: ID!
      status: TaskStatus!
      dueDate: String
      priority: TaskPriority!
      company: Company!
      contact: Contact
      deal: Deal
    }

    type Activity {
      id: ID!
      companyId: ID!
      contactId: ID
      dealId: ID
      userId: ID!
      type: ActivityType!
      details: String!
      occurredAt: String!
      company: Company!
      contact: Contact
      deal: Deal
    }

    input TaskFiltersInput {
      status: TaskStatus
      userId: ID
      dueBefore: String
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

    input CreateTaskInput {
      title: String!
      companyId: ID!
      contactId: ID
      dealId: ID
      userId: ID!
      dueDate: String
      priority: TaskPriority!
    }

    input UpdateTaskInput {
      taskId: ID!
      title: String
      status: TaskStatus
      dueDate: String
      priority: TaskPriority
    }

    input CreateActivityInput {
      companyId: ID!
      contactId: ID
      dealId: ID
      userId: ID!
      type: ActivityType!
      details: String!
      occurredAt: String!
    }

    extend type Query {
      companies: [Company!]!
      company(id: ID!): Company
      contact(id: ID!): Contact
      tasks(filters: TaskFiltersInput): [Task!]!
      activities(companyId: ID, dealId: ID, contactId: ID): [Activity!]!
    }

    type Mutation {
      createCompany(input: CreateCompanyInput!): Company!
      updateCompany(input: UpdateCompanyInput!): Company!
      createContact(input: CreateContactInput!): Contact!
      updateContact(input: UpdateContactInput!): Contact!
      createTask(input: CreateTaskInput!): Task!
      updateTask(input: UpdateTaskInput!): Task!
      createActivity(input: CreateActivityInput!): Activity!
    }
    """
)

query = QueryType()
mutation = MutationType()
company = FederatedObjectType("Company")
contact = FederatedObjectType("Contact")
task = ObjectType("Task")
activity = ObjectType("Activity")
task_status = EnumType(
    "TaskStatus",
    {
        "OPEN": TaskStatus.OPEN,
        "COMPLETED": TaskStatus.COMPLETED,
    },
)
task_priority = EnumType(
    "TaskPriority",
    {
        "LOW": TaskPriority.LOW,
        "MEDIUM": TaskPriority.MEDIUM,
        "HIGH": TaskPriority.HIGH,
    },
)
activity_type = EnumType(
    "ActivityType",
    {
        "CALL": ActivityType.CALL,
        "EMAIL": ActivityType.EMAIL,
        "MEETING": ActivityType.MEETING,
        "NOTE": ActivityType.NOTE,
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


def require_admin_user(info):
    user = require_authenticated_user(info)

    if user["role"] != "admin":
        raise GraphQLError(
            "Only admins can modify companies and contacts.",
            extensions={"code": "FORBIDDEN"},
        )

    return user


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


def get_visible_companies(info) -> QuerySet[Company]:
    user = require_authenticated_user(info)
    queryset = Company.objects.select_related("parent_company").all()

    if user["role"] == "admin":
        return queryset

    if not user["companyId"]:
        return queryset.none()

    return queryset.filter(id=user["companyId"])


def get_visible_tasks(info) -> QuerySet[Task]:
    visible_companies = get_visible_companies(info).values("id")
    return Task.objects.filter(company_id__in=visible_companies)


def get_visible_activities(info) -> QuerySet[Activity]:
    visible_companies = get_visible_companies(info).values("id")
    return Activity.objects.filter(company_id__in=visible_companies)


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


def normalize_optional_id(value):
    return normalize_optional_text(value)


def normalize_required_id(value, field_name):
    normalized_value = normalize_optional_id(value)

    if normalized_value is None:
        raise GraphQLError(
            f"{field_name} is required.",
            extensions={"code": "BAD_USER_INPUT"},
        )

    return normalized_value


def parse_optional_date(value, field_name):
    normalized_value = normalize_optional_text(value)

    if normalized_value is None:
        return None

    try:
        return date.fromisoformat(normalized_value)
    except ValueError as exc:
        raise GraphQLError(
            f"{field_name} must be a valid ISO date.",
            extensions={"code": "BAD_USER_INPUT"},
        ) from exc


def parse_required_datetime(value, field_name):
    normalized_value = normalize_required_text(value, field_name)

    try:
        parsed = datetime.fromisoformat(normalized_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GraphQLError(
            f"{field_name} must be a valid ISO datetime.",
            extensions={"code": "BAD_USER_INPUT"},
        ) from exc

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def format_optional_date(value):
    return value.isoformat() if value else None


def format_datetime_utc(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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
    except (Company.DoesNotExist, ValidationError, ValueError) as exc:
        raise GraphQLError(
            message,
            extensions={"code": "BAD_USER_INPUT"},
        ) from exc


def get_contact_or_error(contact_id, message):
    try:
        return Contact.objects.select_related("company").get(id=contact_id)
    except (Contact.DoesNotExist, ValidationError, ValueError) as exc:
        raise GraphQLError(
            message,
            extensions={"code": "BAD_USER_INPUT"},
        ) from exc


def get_visible_task_or_error(info, task_id):
    try:
        return get_visible_tasks(info).get(id=task_id)
    except (Task.DoesNotExist, ValidationError, ValueError) as exc:
        raise GraphQLError(
            "Task not found.",
            extensions={"code": "BAD_USER_INPUT"},
        ) from exc


def validate_task_status_transition(current_status, next_status):
    if current_status == next_status:
        return

    if current_status == TaskStatus.OPEN and next_status == TaskStatus.COMPLETED:
        return

    raise GraphQLError(
        f"Cannot change task status from {current_status} to {next_status}.",
        extensions={"code": "BAD_USER_INPUT"},
    )


def build_deals_graphql_request_context(info):
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


def execute_deals_query(info, query_text, variables):
    payload = json.dumps(
        {
            "query": query_text,
            "variables": variables,
        }
    ).encode("utf-8")
    graphql_request = request.Request(
        settings.DEALS_GRAPHQL_URL,
        data=payload,
        headers=build_deals_graphql_request_context(info),
        method="POST",
    )

    try:
        with request.urlopen(
            graphql_request,
            timeout=settings.DEALS_GRAPHQL_TIMEOUT_SECONDS,
        ) as response:
            response_payload = json.load(response)
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GraphQLError(
            "Deal validation is unavailable.",
            extensions={"code": "INTERNAL_SERVER_ERROR"},
        ) from exc

    if response_payload.get("errors"):
        raise GraphQLError(
            "Deal validation failed.",
            extensions={"code": "INTERNAL_SERVER_ERROR"},
        )

    return response_payload.get("data", {})


def fetch_deal_reference(info, deal_id):
    data = execute_deals_query(
        info,
        """
        query ValidateDealReference($dealId: ID!) {
          deal(id: $dealId) {
            id
            companyId
          }
        }
        """,
        {"dealId": str(deal_id)},
    )
    return data.get("deal")


def validate_relationship_ids(info, *, company_id, contact_id=None, deal_id=None):
    company_instance = get_company_or_error(company_id, "Company not found.")
    require_company_scope(info, company_instance.id)

    normalized_contact_id = normalize_optional_id(contact_id)
    if normalized_contact_id is not None:
        contact_instance = get_contact_or_error(
            normalized_contact_id,
            "Contact not found.",
        )
        if contact_instance.company_id != company_instance.id:
            raise GraphQLError(
                "Contact must belong to the selected company.",
                extensions={"code": "BAD_USER_INPUT"},
            )

    normalized_deal_id = normalize_optional_id(deal_id)
    if normalized_deal_id is not None:
        deal_reference = fetch_deal_reference(info, normalized_deal_id)
        if deal_reference is None:
            raise GraphQLError(
                "Deal not found.",
                extensions={"code": "BAD_USER_INPUT"},
            )
        if deal_reference["companyId"] != str(company_instance.id):
            raise GraphQLError(
                "Deal must belong to the selected company.",
                extensions={"code": "BAD_USER_INPUT"},
            )

    return company_instance


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
    instance.job_title = normalize_optional_text(input_data.get("jobTitle", "")) or ""


def save_contact(instance):
    try:
        instance.full_clean()
    except ValidationError as error:
        raise_validation_error(error)

    instance.save()
    return instance


def save_task(instance):
    try:
        instance.full_clean()
    except ValidationError as error:
        raise_validation_error(error)

    instance.save()
    return instance


def save_activity(instance):
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


@query.field("tasks")
def resolve_tasks(_, info, filters=None):
    queryset = get_visible_tasks(info)
    filter_values = filters or {}

    status = filter_values.get("status")
    if status is not None:
        queryset = queryset.filter(status=status)

    user_id = normalize_optional_id(filter_values.get("userId"))
    if user_id is not None:
        queryset = queryset.filter(user_id=user_id)

    due_before = parse_optional_date(filter_values.get("dueBefore"), "Due before")
    if due_before is not None:
        queryset = queryset.filter(due_date__lte=due_before)

    return queryset


@query.field("activities")
def resolve_activities(_, info, companyId=None, dealId=None, contactId=None):
    queryset = get_visible_activities(info)

    try:
        if companyId is not None:
            queryset = queryset.filter(company_id=companyId)
        if dealId is not None:
            queryset = queryset.filter(deal_id=dealId)
        if contactId is not None:
            queryset = queryset.filter(contact_id=contactId)
    except (ValidationError, ValueError):
        return Activity.objects.none()

    return queryset


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


@mutation.field("createTask")
def resolve_create_task(_, info, input):
    require_authenticated_user(info)

    title = normalize_required_text(input["title"], "Title")
    company_id = normalize_required_id(input["companyId"], "Company")
    contact_id = normalize_optional_id(input.get("contactId"))
    deal_id = normalize_optional_id(input.get("dealId"))
    user_id = normalize_required_id(input["userId"], "User")
    due_date = parse_optional_date(input.get("dueDate"), "Due date")
    priority = input["priority"]

    validate_relationship_ids(
        info,
        company_id=company_id,
        contact_id=contact_id,
        deal_id=deal_id,
    )

    instance = Task(
        title=title,
        company_id=company_id,
        contact_id=contact_id,
        deal_id=deal_id,
        user_id=user_id,
        due_date=due_date,
        priority=priority,
    )
    return save_task(instance)


@mutation.field("updateTask")
def resolve_update_task(_, info, input):
    require_authenticated_user(info)

    instance = get_visible_task_or_error(
        info,
        normalize_required_id(input["taskId"], "Task"),
    )

    has_changes = False

    if "title" in input and input["title"] is not None:
        instance.title = normalize_required_text(input["title"], "Title")
        has_changes = True

    if "status" in input and input["status"] is not None:
        validate_task_status_transition(instance.status, input["status"])
        instance.status = input["status"]
        has_changes = True

    if "dueDate" in input:
        instance.due_date = parse_optional_date(input.get("dueDate"), "Due date")
        has_changes = True

    if "priority" in input and input["priority"] is not None:
        instance.priority = input["priority"]
        has_changes = True

    if not has_changes:
        return instance

    return save_task(instance)


@mutation.field("createActivity")
def resolve_create_activity(_, info, input):
    require_authenticated_user(info)

    company_id = normalize_required_id(input["companyId"], "Company")
    contact_id = normalize_optional_id(input.get("contactId"))
    deal_id = normalize_optional_id(input.get("dealId"))
    user_id = normalize_required_id(input["userId"], "User")
    details = normalize_required_text(input["details"], "Details")
    occurred_at = parse_required_datetime(input["occurredAt"], "Occurred at")

    validate_relationship_ids(
        info,
        company_id=company_id,
        contact_id=contact_id,
        deal_id=deal_id,
    )

    instance = Activity(
        company_id=company_id,
        contact_id=contact_id,
        deal_id=deal_id,
        user_id=user_id,
        type=input["type"],
        details=details,
        occurred_at=occurred_at,
    )
    return save_activity(instance)


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


@task.field("companyId")
def resolve_task_company_id(obj, _info):
    return str(obj.company_id)


@task.field("contactId")
def resolve_task_contact_id(obj, _info):
    return str(obj.contact_id) if obj.contact_id else None


@task.field("dealId")
def resolve_task_deal_id(obj, _info):
    return str(obj.deal_id) if obj.deal_id else None


@task.field("userId")
def resolve_task_user_id(obj, _info):
    return str(obj.user_id)


@task.field("dueDate")
def resolve_task_due_date(obj, _info):
    return format_optional_date(obj.due_date)


@task.field("company")
def resolve_task_company(obj, _info):
    return Company.objects.filter(id=obj.company_id).first()


@task.field("contact")
def resolve_task_contact(obj, _info):
    if obj.contact_id is None:
        return None

    return Contact.objects.select_related("company").filter(
        id=obj.contact_id,
        company_id=obj.company_id,
    ).first()


@task.field("deal")
def resolve_task_deal(obj, _info):
    if obj.deal_id is None:
        return None

    return {"id": str(obj.deal_id)}


@activity.field("companyId")
def resolve_activity_company_id(obj, _info):
    return str(obj.company_id)


@activity.field("contactId")
def resolve_activity_contact_id(obj, _info):
    return str(obj.contact_id) if obj.contact_id else None


@activity.field("dealId")
def resolve_activity_deal_id(obj, _info):
    return str(obj.deal_id) if obj.deal_id else None


@activity.field("userId")
def resolve_activity_user_id(obj, _info):
    return str(obj.user_id)


@activity.field("occurredAt")
def resolve_activity_occurred_at(obj, _info):
    return format_datetime_utc(obj.occurred_at)


@activity.field("company")
def resolve_activity_company(obj, _info):
    return Company.objects.filter(id=obj.company_id).first()


@activity.field("contact")
def resolve_activity_contact(obj, _info):
    if obj.contact_id is None:
        return None

    return Contact.objects.select_related("company").filter(
        id=obj.contact_id,
        company_id=obj.company_id,
    ).first()


@activity.field("deal")
def resolve_activity_deal(obj, _info):
    if obj.deal_id is None:
        return None

    return {"id": str(obj.deal_id)}


schema = make_federated_schema(
    type_defs,
    [
        query,
        mutation,
        company,
        contact,
        task,
        activity,
        task_status,
        task_priority,
        activity_type,
    ],
)
