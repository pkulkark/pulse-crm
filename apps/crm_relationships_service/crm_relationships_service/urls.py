from django.http import JsonResponse
from django.urls import include, path


def placeholder_root(_request):
    return JsonResponse(
        {
            "service": "crm-relationships-service",
            "message": "Sample GraphQL subgraph placeholder. CRM relationships implementation starts in a later slice.",
            "health": "/health/",
            "graphql": "/graphql/",
        },
    )


urlpatterns = [
    path("", placeholder_root),
    path("", include("apps.health.urls")),
]
