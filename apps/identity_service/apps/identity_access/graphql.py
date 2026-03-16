from ariadne import EnumType, MutationType, ObjectType, QueryType, gql
from ariadne.contrib.federation import make_federated_schema
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from graphql import GraphQLError

from apps.users.models import UserRole

from .tokens import create_access_token


type_defs = gql(
    """
    enum UserRole {
      ADMIN
      MANAGER
      SALES_REP
    }

    type User {
      id: ID!
      companyId: ID!
      name: String!
      email: String!
      role: UserRole!
    }

    type AuthPayload {
      token: String!
      user: User!
    }

    input LoginInput {
      email: String!
      password: String!
    }

    type Query {
      me: User
      users(role: UserRole): [User!]!
    }

    type Mutation {
      login(input: LoginInput!): AuthPayload!
    }
    """
)

query = QueryType()
mutation = MutationType()
user = ObjectType("User")
user_role = EnumType(
    "UserRole",
    {
        "ADMIN": UserRole.ADMIN,
        "MANAGER": UserRole.MANAGER,
        "SALES_REP": UserRole.SALES_REP,
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


def require_user_directory_access(info):
    user = require_authenticated_user(info)

    if user["role"] not in {UserRole.ADMIN, UserRole.MANAGER}:
        raise GraphQLError(
            "Only admins and managers can view assignable users.",
            extensions={"code": "FORBIDDEN"},
        )

    return user


@user.field("companyId")
def resolve_user_company_id(obj, _info):
    return str(obj.company_id)


@query.field("me")
def resolve_me(_, info):
    user_id = info.context["request_context"]["user"]["id"]

    if not user_id:
        return None

    user_model = get_user_model()
    return user_model.objects.filter(id=user_id, is_active=True).first()


@query.field("users")
def resolve_users(_, info, role=None):
    require_user_directory_access(info)

    user_model = get_user_model()
    queryset = user_model.objects.filter(is_active=True).order_by("name", "email")

    if role is not None:
        queryset = queryset.filter(role=role)

    return queryset


@mutation.field("login")
def resolve_login(_, _info, input):
    email = input["email"].strip().lower()
    password = input["password"]

    try:
        validate_email(email)
    except Exception as error:
        raise GraphQLError(
            "Enter a valid email address.",
            extensions={"code": "BAD_USER_INPUT"},
        ) from error

    user_model = get_user_model()
    authenticated_user = (
        user_model.objects.filter(email=email, is_active=True).first()
    )

    if authenticated_user is None or not authenticated_user.check_password(password):
        raise GraphQLError(
            "Invalid email or password.",
            extensions={"code": "UNAUTHENTICATED"},
        )

    return {
        "token": create_access_token(authenticated_user),
        "user": authenticated_user,
    }


schema = make_federated_schema(type_defs, [query, mutation, user, user_role])
