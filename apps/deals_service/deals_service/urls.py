from django.urls import include, path


urlpatterns = [
    path("", include("apps.deals.urls")),
    path("", include("apps.health.urls")),
]
