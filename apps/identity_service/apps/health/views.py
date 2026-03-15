from django.http import JsonResponse


def health_check(_request):
    return JsonResponse(
        {
            "service": "identity-service",
            "status": "ok",
        },
    )
