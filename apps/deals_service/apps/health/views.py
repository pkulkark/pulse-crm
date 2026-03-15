from django.http import JsonResponse


def health_check(_request):
    return JsonResponse(
        {
            "service": "deals-service",
            "status": "ok",
        },
    )
