import json

from django.contrib.auth import get_user_model
from django.test import TestCase


class IdentityAccessTests(TestCase):
    def test_seeded_users_exist(self):
        user_model = get_user_model()

        self.assertTrue(user_model.objects.filter(email="admin@example.com").exists())
        self.assertTrue(
            user_model.objects.filter(email="manager@example.com").exists(),
        )

    def test_login_returns_token_and_user(self):
        response = self.client.post(
            "/graphql/",
            data=json.dumps(
                {
                    "query": """
                        mutation Login($input: LoginInput!) {
                            login(input: $input) {
                                token
                                user {
                                    id
                                    companyId
                                    name
                                    email
                                    role
                                }
                            }
                        }
                    """,
                    "variables": {
                        "input": {
                            "email": "admin@example.com",
                            "password": "secret",
                        }
                    },
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]["login"]
        self.assertTrue(payload["token"])
        self.assertEqual(payload["user"]["email"], "admin@example.com")
        self.assertEqual(payload["user"]["role"], "ADMIN")

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            "/graphql/",
            data=json.dumps(
                {
                    "query": """
                        mutation Login($input: LoginInput!) {
                            login(input: $input) {
                                token
                            }
                        }
                    """,
                    "variables": {
                        "input": {
                            "email": "admin@example.com",
                            "password": "wrong-password",
                        }
                    },
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["errors"][0]["message"],
            "Invalid email or password.",
        )

    def test_me_returns_authenticated_user_from_trusted_context(self):
        user = get_user_model().objects.get(email="manager@example.com")

        response = self.client.post(
            "/graphql/",
            data=json.dumps(
                {
                    "query": """
                        query Me {
                            me {
                                id
                                companyId
                                email
                                role
                            }
                        }
                    """
                }
            ),
            content_type="application/json",
            HTTP_X_USER_ID=str(user.id),
            HTTP_X_USER_ROLE=user.role,
            HTTP_X_COMPANY_ID=str(user.company_id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"]["me"],
            {
                "id": str(user.id),
                "companyId": str(user.company_id),
                "email": "manager@example.com",
                "role": "MANAGER",
            },
        )

    def test_me_returns_null_when_request_is_unauthenticated(self):
        response = self.client.post(
            "/graphql/",
            data=json.dumps(
                {
                    "query": """
                        query Me {
                            me {
                                id
                            }
                        }
                    """
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"]["me"])
