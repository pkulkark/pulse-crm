from django.urls import re_path

from .views import graphql_endpoint


urlpatterns = [
    re_path(r"^graphql/?$", graphql_endpoint, name="graphql"),
]

