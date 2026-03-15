from django.http import JsonResponse
from django.urls import include, path


def placeholder_root(_request):
    return JsonResponse(
        {
            "service": "crm-relationships-service",
            "message": "Phase 0 placeholder. CRM relationships implementation starts in Phase 3.",
            "health": "/health/",
        },
    )


urlpatterns = [
    path("", placeholder_root),
    path("", include("apps.health.urls")),
]

