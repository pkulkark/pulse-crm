import json
import uuid
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from .models import Deal, DealStatus


class DealGraphQLSchemaTests(SimpleTestCase):
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
        self.assertIn("type Deal", response.json()["data"]["_service"]["sdl"])


class DealGraphQLTests(TestCase):
    def graphql(self, query, *, variables=None, headers=None):
        request_headers = headers or {}
        return self.client.post(
            "/graphql/",
            data=json.dumps(
                {
                    "query": query,
                    "variables": variables or {},
                }
            ),
            content_type="application/json",
            **request_headers,
        )

    def admin_headers(self):
        return {
            "HTTP_X_COMPANY_ID": str(uuid.UUID("11111111-1111-1111-1111-111111111111")),
            "HTTP_X_USER_ID": str(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")),
            "HTTP_X_USER_ROLE": "admin",
        }

    def manager_headers(self, company_id):
        return {
            "HTTP_X_COMPANY_ID": str(company_id),
            "HTTP_X_USER_ID": str(uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")),
            "HTTP_X_USER_ROLE": "manager",
        }

    @patch("apps.deals.graphql.fetch_reference_records")
    def test_create_deal_supports_optional_primary_contact(self, mock_fetch_reference_records):
        company_id = uuid.uuid4()
        contact_id = uuid.uuid4()
        mock_fetch_reference_records.side_effect = [
            {"company": {"id": str(company_id)}},
            {
                "company": {"id": str(company_id)},
                "contact": {
                    "id": str(contact_id),
                    "companyId": str(company_id),
                },
            },
        ]

        without_contact_response = self.graphql(
            """
                mutation CreateDeal($input: CreateDealInput!) {
                    createDeal(input: $input) {
                        id
                        companyId
                        primaryContactId
                        status
                    }
                }
            """,
            variables={
                "input": {
                    "companyId": str(company_id),
                    "status": "NEW",
                }
            },
            headers=self.admin_headers(),
        )
        with_contact_response = self.graphql(
            """
                mutation CreateDeal($input: CreateDealInput!) {
                    createDeal(input: $input) {
                        id
                        companyId
                        primaryContactId
                        status
                    }
                }
            """,
            variables={
                "input": {
                    "companyId": str(company_id),
                    "primaryContactId": str(contact_id),
                    "status": "QUALIFIED",
                }
            },
            headers=self.admin_headers(),
        )

        self.assertEqual(without_contact_response.status_code, 200)
        self.assertEqual(
            without_contact_response.json()["data"]["createDeal"]["primaryContactId"],
            None,
        )
        self.assertEqual(with_contact_response.status_code, 200)
        self.assertEqual(
            with_contact_response.json()["data"]["createDeal"],
            {
                "id": str(Deal.objects.order_by("created_at").last().id),
                "companyId": str(company_id),
                "primaryContactId": str(contact_id),
                "status": "QUALIFIED",
            },
        )

    @patch("apps.deals.graphql.fetch_reference_records")
    def test_create_deal_rejects_invalid_references(self, mock_fetch_reference_records):
        company_id = uuid.uuid4()
        contact_id = uuid.uuid4()
        other_company_id = uuid.uuid4()
        mock_fetch_reference_records.side_effect = [
            {"company": None},
            {
                "company": {"id": str(company_id)},
                "contact": {
                    "id": str(contact_id),
                    "companyId": str(other_company_id),
                },
            },
        ]

        missing_company_response = self.graphql(
            """
                mutation CreateDeal($input: CreateDealInput!) {
                    createDeal(input: $input) {
                        id
                    }
                }
            """,
            variables={
                "input": {
                    "companyId": str(company_id),
                    "status": "NEW",
                }
            },
            headers=self.admin_headers(),
        )
        wrong_contact_response = self.graphql(
            """
                mutation CreateDeal($input: CreateDealInput!) {
                    createDeal(input: $input) {
                        id
                    }
                }
            """,
            variables={
                "input": {
                    "companyId": str(company_id),
                    "primaryContactId": str(contact_id),
                    "status": "NEW",
                }
            },
            headers=self.admin_headers(),
        )

        self.assertEqual(
            missing_company_response.json()["errors"][0]["message"],
            "Company not found.",
        )
        self.assertEqual(
            wrong_contact_response.json()["errors"][0]["message"],
            "Primary contact must belong to the selected company.",
        )

    @patch("apps.deals.graphql.fetch_reference_records")
    def test_company_scope_is_enforced_for_create_deal(self, mock_fetch_reference_records):
        company_id = uuid.uuid4()

        response = self.graphql(
            """
                mutation CreateDeal($input: CreateDealInput!) {
                    createDeal(input: $input) {
                        id
                    }
                }
            """,
            variables={
                "input": {
                    "companyId": str(company_id),
                    "status": "NEW",
                }
            },
            headers=self.manager_headers(uuid.uuid4()),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["errors"][0]["extensions"]["code"],
            "FORBIDDEN",
        )
        mock_fetch_reference_records.assert_not_called()

    def test_reads_are_filtered_by_company_scope_and_include_federated_references(self):
        visible_company_id = uuid.uuid4()
        hidden_company_id = uuid.uuid4()
        contact_id = uuid.uuid4()
        visible_deal = Deal.objects.create(
            company_id=visible_company_id,
            primary_contact_id=contact_id,
            status=DealStatus.NEW,
        )
        Deal.objects.create(
            company_id=hidden_company_id,
            status=DealStatus.QUALIFIED,
        )

        response = self.graphql(
            """
                query Deals($visibleId: ID!, $hiddenId: ID!) {
                    deals {
                        id
                        companyId
                        primaryContactId
                        company {
                            id
                        }
                        primaryContact {
                            id
                        }
                    }
                    visible: deal(id: $visibleId) {
                        id
                    }
                    hidden: deal(id: $hiddenId) {
                        id
                    }
                }
            """,
            variables={
                "visibleId": str(visible_deal.id),
                "hiddenId": str(Deal.objects.exclude(id=visible_deal.id).get().id),
            },
            headers=self.manager_headers(visible_company_id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"]["deals"],
            [
                {
                    "id": str(visible_deal.id),
                    "companyId": str(visible_company_id),
                    "primaryContactId": str(contact_id),
                    "company": {"id": str(visible_company_id)},
                    "primaryContact": {"id": str(contact_id)},
                }
            ],
        )
        self.assertEqual(
            response.json()["data"]["visible"]["id"],
            str(visible_deal.id),
        )
        self.assertIsNone(response.json()["data"]["hidden"])

    def test_update_deal_status_persists_valid_transition(self):
        deal = Deal.objects.create(
            company_id=uuid.uuid4(),
            status=DealStatus.NEW,
        )

        response = self.graphql(
            """
                mutation UpdateDealStatus($input: UpdateDealStatusInput!) {
                    updateDealStatus(input: $input) {
                        id
                        status
                    }
                }
            """,
            variables={
                "input": {
                    "dealId": str(deal.id),
                    "status": "QUALIFIED",
                }
            },
            headers=self.admin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        deal.refresh_from_db()
        self.assertEqual(deal.status, DealStatus.QUALIFIED)
        self.assertEqual(
            response.json()["data"]["updateDealStatus"]["status"],
            "QUALIFIED",
        )

    def test_update_deal_status_rejects_invalid_transition(self):
        deal = Deal.objects.create(
            company_id=uuid.uuid4(),
            status=DealStatus.LOST,
        )

        response = self.graphql(
            """
                mutation UpdateDealStatus($input: UpdateDealStatusInput!) {
                    updateDealStatus(input: $input) {
                        id
                        status
                    }
                }
            """,
            variables={
                "input": {
                    "dealId": str(deal.id),
                    "status": "QUALIFIED",
                }
            },
            headers=self.admin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["errors"][0]["message"],
            "Cannot change deal status from LOST to QUALIFIED.",
        )
        deal.refresh_from_db()
        self.assertEqual(deal.status, DealStatus.LOST)

    def test_deal_reads_require_authentication(self):
        response = self.graphql(
            """
                query Deals {
                    deals {
                        id
                    }
                }
            """
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["errors"][0]["extensions"]["code"],
            "UNAUTHENTICATED",
        )
