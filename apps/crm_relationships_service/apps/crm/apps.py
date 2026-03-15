from django.apps import AppConfig


class CrmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.crm"

    def ready(self):
        from .consumer import start_consumer_thread

        start_consumer_thread()
