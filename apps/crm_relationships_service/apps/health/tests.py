import json

from django.test import SimpleTestCase


class HealthCheckTests(SimpleTestCase):
    def test_health_endpoint_returns_ok(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

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
        self.assertIn("type Company", response.json()["data"]["_service"]["sdl"])
