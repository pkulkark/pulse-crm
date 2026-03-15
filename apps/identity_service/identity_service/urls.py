from django.http import JsonResponse
from django.urls import include, path


def placeholder_root(_request):
    return JsonResponse(
        {
            "service": "identity-service",
            "message": "Phase 0 placeholder. Identity flows start in Phase 2.",
            "health": "/health/",
        },
    )


urlpatterns = [
    path("", placeholder_root),
    path("", include("apps.health.urls")),
]

