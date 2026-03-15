from django.urls import include, path

urlpatterns = [
    path("", include("apps.identity_access.urls")),
    path("", include("apps.health.urls")),
]
