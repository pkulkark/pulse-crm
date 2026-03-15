from django.http import JsonResponse


def health_check(_request):
    return JsonResponse(
        {
            "service": "crm-relationships-service",
            "status": "ok",
            "phase": "phase-0",
        },
    )

