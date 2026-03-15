import json

from django.test import SimpleTestCase


class HealthCheckTests(SimpleTestCase):
    def test_health_endpoint_returns_ok(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_graphql_service_health_returns_forwarded_request_context(self):
        response = self.client.post(
            "/graphql/",
            data=json.dumps(
                {
                    "query": """
                        query ServiceHealth {
                            serviceHealth {
                                service
                                status
                                requestContext {
                                    correlationId
                                    userId
                                    userRole
                                }
                            }
                        }
                    """
                }
            ),
            content_type="application/json",
            HTTP_X_CORRELATION_ID="corr-123",
            HTTP_X_USER_ID="user-7",
            HTTP_X_USER_ROLE="manager",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"]["serviceHealth"],
            {
                "requestContext": {
                    "correlationId": "corr-123",
                    "userId": "user-7",
                    "userRole": "manager",
                },
                "service": "crm-relationships-service",
                "status": "ok",
            },
        )

    def test_graphql_endpoint_exposes_federation_service_definition(self):
        response = self.client.post(
            "/graphql/",
            data=json.dumps(
                {
                    "query": """
                        query ServiceDefinition {
                            _service {
                                sdl
                            }
                        }
                    """
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("serviceHealth", response.json()["data"]["_service"]["sdl"])
