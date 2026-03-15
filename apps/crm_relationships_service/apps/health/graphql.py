from ariadne import QueryType, gql
from ariadne.contrib.federation import make_federated_schema


type_defs = gql(
    """
    type RequestContext {
      companyId: String
      correlationId: ID!
      userId: String
      userRole: String!
    }

    type ServiceHealth {
      service: String!
      status: String!
      requestContext: RequestContext!
    }

    type Query {
      serviceHealth: ServiceHealth!
    }
    """
)

query = QueryType()


@query.field("serviceHealth")
def resolve_service_health(_, info):
    request_context = info.context["request_context"]

    return {
        "requestContext": request_context,
        "service": "crm-relationships-service",
        "status": "ok",
    }


schema = make_federated_schema(type_defs, query)
