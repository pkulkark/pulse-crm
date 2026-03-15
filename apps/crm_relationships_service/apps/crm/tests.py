import json
import uuid

from django.test import TestCase

from .models import Company, Contact


class CrmGraphQLTests(TestCase):
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

    def test_admin_can_create_parent_and_child_companies(self):
        response = self.graphql(
            """
                mutation CreateCompany($input: CreateCompanyInput!) {
                    createCompany(input: $input) {
                        id
                        name
                        parentCompanyId
                    }
                }
            """,
            variables={"input": {"name": "BrightCo"}},
            headers=self.admin_headers(),
        )
        self.assertEqual(response.status_code, 200)
        parent_company = response.json()["data"]["createCompany"]

        response = self.graphql(
            """
                mutation CreateCompany($input: CreateCompanyInput!) {
                    createCompany(input: $input) {
                        id
                        name
                        parentCompanyId
                    }
                }
            """,
            variables={
                "input": {
                    "name": "BrightCo Canada",
                    "parentCompanyId": parent_company["id"],
                }
            },
            headers=self.admin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"]["createCompany"]["parentCompanyId"],
            parent_company["id"],
        )

    def test_company_detail_exposes_hierarchy_and_contacts(self):
        parent_company = Company.objects.create(name="Northwind")
        child_company = Company.objects.create(
            name="Northwind East",
            parent_company=parent_company,
        )
        contact = Contact.objects.create(
            company=parent_company,
            name="Alice Johnson",
            email="alice@northwind.test",
            job_title="CEO",
        )

        response = self.graphql(
            """
                query CompanyDetail($id: ID!) {
                    company(id: $id) {
                        id
                        name
                        parentCompany {
                            id
                            name
                        }
                        childCompanies {
                            id
                            name
                        }
                        contacts {
                            id
                            name
                            email
                            jobTitle
                        }
                    }
                }
            """,
            variables={"id": str(parent_company.id)},
            headers=self.admin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"]["company"],
            {
                "id": str(parent_company.id),
                "name": "Northwind",
                "parentCompany": None,
                "childCompanies": [
                    {
                        "id": str(child_company.id),
                        "name": "Northwind East",
                    }
                ],
                "contacts": [
                    {
                        "id": str(contact.id),
                        "name": "Alice Johnson",
                        "email": "alice@northwind.test",
                        "jobTitle": "CEO",
                    }
                ],
            },
        )

    def test_admin_can_create_contact_for_company(self):
        company = Company.objects.create(name="Contoso")

        response = self.graphql(
            """
                mutation CreateContact($input: CreateContactInput!) {
                    createContact(input: $input) {
                        id
                        companyId
                        name
                        email
                        jobTitle
                    }
                }
            """,
            variables={
                "input": {
                    "companyId": str(company.id),
                    "name": "Pat Lee",
                    "email": "PAT.LEE@CONTOSO.TEST",
                    "jobTitle": "VP Sales",
                }
            },
            headers=self.admin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]["createContact"]
        self.assertEqual(payload["companyId"], str(company.id))
        self.assertEqual(payload["email"], "pat.lee@contoso.test")

    def test_non_admin_users_cannot_modify_companies_or_contacts(self):
        company = Company.objects.create(name="Fabrikam")
        contact = Contact.objects.create(
            company=company,
            name="Jordan Miles",
            email="jordan@fabrikam.test",
        )
        headers = self.manager_headers(company.id)

        create_company_response = self.graphql(
            """
                mutation CreateCompany($input: CreateCompanyInput!) {
                    createCompany(input: $input) {
                        id
                    }
                }
            """,
            variables={"input": {"name": "Blocked Company"}},
            headers=headers,
        )
        update_contact_response = self.graphql(
            """
                mutation UpdateContact($input: UpdateContactInput!) {
                    updateContact(input: $input) {
                        id
                    }
                }
            """,
            variables={
                "input": {
                    "contactId": str(contact.id),
                    "name": contact.name,
                    "email": contact.email,
                    "jobTitle": "Director",
                }
            },
            headers=headers,
        )

        self.assertEqual(
            create_company_response.json()["errors"][0]["extensions"]["code"],
            "FORBIDDEN",
        )
        self.assertEqual(
            update_contact_response.json()["errors"][0]["extensions"]["code"],
            "FORBIDDEN",
        )

    def test_company_reads_require_authentication(self):
        response = self.graphql(
            """
                query Companies {
                    companies {
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

    def test_non_admin_reads_are_limited_to_current_company_scope(self):
        visible_company = Company.objects.create(name="Visible Co")
        hidden_company = Company.objects.create(name="Hidden Co")
        hidden_contact = Contact.objects.create(
            company=hidden_company,
            name="Hidden Contact",
            email="hidden@company.test",
        )

        response = self.graphql(
            """
                query ScopedReads($companyId: ID!, $contactId: ID!) {
                    companies {
                        id
                        name
                    }
                    company(id: $companyId) {
                        id
                    }
                    contact(id: $contactId) {
                        id
                    }
                }
            """,
            variables={
                "companyId": str(hidden_company.id),
                "contactId": str(hidden_contact.id),
            },
            headers=self.manager_headers(visible_company.id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"],
            {
                "companies": [
                    {
                        "id": str(visible_company.id),
                        "name": "Visible Co",
                    }
                ],
                "company": None,
                "contact": None,
            },
        )

    def test_company_hierarchy_rejects_cycles(self):
        parent_company = Company.objects.create(name="Parent")
        child_company = Company.objects.create(
            name="Child",
            parent_company=parent_company,
        )

        response = self.graphql(
            """
                mutation UpdateCompany($input: UpdateCompanyInput!) {
                    updateCompany(input: $input) {
                        id
                    }
                }
            """,
            variables={
                "input": {
                    "companyId": str(parent_company.id),
                    "name": parent_company.name,
                    "parentCompanyId": str(child_company.id),
                }
            },
            headers=self.admin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["errors"][0]["message"],
            "Company hierarchy cannot contain cycles.",
        )

    def test_contact_email_must_be_unique_within_company(self):
        company = Company.objects.create(name="Woodgrove")
        Contact.objects.create(
            company=company,
            name="Existing Contact",
            email="existing@woodgrove.test",
        )

        response = self.graphql(
            """
                mutation CreateContact($input: CreateContactInput!) {
                    createContact(input: $input) {
                        id
                    }
                }
            """,
            variables={
                "input": {
                    "companyId": str(company.id),
                    "name": "Another Contact",
                    "email": "EXISTING@WOODGROVE.TEST",
                    "jobTitle": "COO",
                }
            },
            headers=self.admin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["errors"][0]["message"],
            "Contact with this Company and Email already exists.",
        )

