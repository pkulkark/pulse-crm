from django.http import JsonResponse
from django.urls import include, path


def placeholder_root(_request):
    return JsonResponse(
        {
            "service": "deals-service",
            "message": "Sample service placeholder. Deal workflows start in a later slice.",
            "health": "/health/",
        },
    )


urlpatterns = [
    path("", placeholder_root),
    path("", include("apps.health.urls")),
]
