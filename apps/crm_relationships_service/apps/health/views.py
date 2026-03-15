import json
import logging
import uuid

from ariadne import graphql_sync
from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .graphql import schema


logger = logging.getLogger(__name__)


def build_request_context(request):
    correlation_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
    user_id = request.headers.get("X-User-Id") or None
    user_role = request.headers.get("X-User-Role") or "anonymous"

    return {
        "correlationId": correlation_id,
        "userId": user_id,
        "userRole": user_role,
    }


def log_graphql_event(event, **fields):
    logger.info(json.dumps({"event": event, **fields}))


def health_check(_request):
    return JsonResponse(
        {
            "graphql": "/graphql/",
            "service": "crm-relationships-service",
            "status": "ok",
        },
    )


@csrf_exempt
def graphql_endpoint(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "errors": [
                    {
                        "message": "Request body must be valid JSON.",
                    },
                ],
            },
            status=400,
        )

    request_context = build_request_context(request)
    log_graphql_event(
        "crm_relationships_graphql_request",
        correlationId=request_context["correlationId"],
        operationName=payload.get("operationName"),
        userId=request_context["userId"],
        userRole=request_context["userRole"],
    )
    success, result = graphql_sync(
        schema,
        payload,
        context_value={"request_context": request_context},
    )
    log_graphql_event(
        "crm_relationships_graphql_response",
        correlationId=request_context["correlationId"],
        errorCount=len(result.get("errors", [])),
    )

    return JsonResponse(result, status=200 if success else 400)
