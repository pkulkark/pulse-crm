from django.http import JsonResponse
from django.urls import include, path


def placeholder_root(_request):
    return JsonResponse(
        {
            "service": "deals-service",
            "message": "Phase 0 placeholder. Deal workflows start in Phase 4.",
            "health": "/health/",
        },
    )


urlpatterns = [
    path("", placeholder_root),
    path("", include("apps.health.urls")),
]

