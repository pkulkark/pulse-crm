from django.urls import path, re_path

from .views import graphql_endpoint, health_check


urlpatterns = [
    re_path(r"^graphql/?$", graphql_endpoint, name="graphql"),
    path("health/", health_check, name="health-check"),
]
