from django.urls import include, path

urlpatterns = [
    path("", include("apps.health.urls")),
]
