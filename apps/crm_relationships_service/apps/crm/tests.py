import json
import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from .consumer import handle_consumer_message
from .models import Activity, Company, Contact, Task, TaskPriority, TaskStatus


DEFAULT_COMPANY_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
ADMIN_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
MANAGER_USER_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


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
            "HTTP_X_COMPANY_ID": str(DEFAULT_COMPANY_ID),
            "HTTP_X_USER_ID": str(ADMIN_USER_ID),
            "HTTP_X_USER_ROLE": "admin",
        }

    def manager_headers(self, company_id):
        return {
            "HTTP_X_COMPANY_ID": str(company_id),
            "HTTP_X_USER_ID": str(MANAGER_USER_ID),
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

    def test_admin_can_create_contact_without_job_title(self):
        company = Company.objects.create(name="No Title Co")

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
                    "name": "Taylor Reed",
                    "email": "taylor@notitle.test",
                }
            },
            headers=self.admin_headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]["createContact"]
        self.assertEqual(payload["companyId"], str(company.id))
        self.assertIsNone(payload["jobTitle"])
        self.assertEqual(
            Contact.objects.get(id=payload["id"]).job_title,
            "",
        )

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

    @patch("apps.crm.graphql.fetch_deal_reference")
    def test_create_task_supports_company_contact_and_deal_references(
        self,
        mock_fetch_deal_reference,
    ):
        company = Company.objects.create(name="Litware")
        contact = Contact.objects.create(
            company=company,
            name="Jamie Chen",
            email="jamie@litware.test",
        )
        deal_id = str(uuid.uuid4())
        mock_fetch_deal_reference.return_value = {
            "id": deal_id,
            "companyId": str(company.id),
        }

        response = self.graphql(
            """
                mutation CreateTask($input: CreateTaskInput!) {
                    createTask(input: $input) {
                        id
                        title
                        companyId
                        contactId
                        dealId
                        userId
                        status
                        dueDate
                        priority
                        company {
                            id
                            name
                        }
                        contact {
                            id
                            name
                        }
                        deal {
                            id
                        }
                    }
                }
            """,
            variables={
                "input": {
                    "title": "Prepare renewal summary",
                    "companyId": str(company.id),
                    "contactId": str(contact.id),
                    "dealId": deal_id,
                    "userId": str(MANAGER_USER_ID),
                    "dueDate": "2026-03-20",
                    "priority": "HIGH",
                }
            },
            headers=self.manager_headers(company.id),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]["createTask"]
        self.assertEqual(payload["title"], "Prepare renewal summary")
        self.assertEqual(payload["companyId"], str(company.id))
        self.assertEqual(payload["contactId"], str(contact.id))
        self.assertEqual(payload["dealId"], deal_id)
        self.assertEqual(payload["userId"], str(MANAGER_USER_ID))
        self.assertEqual(payload["status"], TaskStatus.OPEN)
        self.assertEqual(payload["dueDate"], "2026-03-20")
        self.assertEqual(payload["priority"], TaskPriority.HIGH)
        self.assertEqual(payload["company"]["name"], "Litware")
        self.assertEqual(payload["contact"]["name"], "Jamie Chen")
        self.assertEqual(payload["deal"]["id"], deal_id)

    def test_tasks_support_status_assignee_and_due_date_filters(self):
        visible_company = Company.objects.create(name="Visible Co")
        hidden_company = Company.objects.create(name="Hidden Co")
        visible_contact = Contact.objects.create(
            company=visible_company,
            name="Visible Contact",
            email="visible@company.test",
        )
        matching_task = Task.objects.create(
            title="Call customer",
            company_id=visible_company.id,
            contact_id=visible_contact.id,
            deal_id=uuid.uuid4(),
            user_id=MANAGER_USER_ID,
            status=TaskStatus.OPEN,
            due_date=date(2026, 3, 20),
            priority=TaskPriority.HIGH,
        )
        Task.objects.create(
            title="Too late",
            company_id=visible_company.id,
            user_id=MANAGER_USER_ID,
            status=TaskStatus.OPEN,
            due_date=date(2026, 3, 25),
            priority=TaskPriority.MEDIUM,
        )
        Task.objects.create(
            title="Wrong assignee",
            company_id=visible_company.id,
            user_id=uuid.uuid4(),
            status=TaskStatus.OPEN,
            due_date=date(2026, 3, 20),
            priority=TaskPriority.MEDIUM,
        )
        Task.objects.create(
            title="Already completed",
            company_id=visible_company.id,
            user_id=MANAGER_USER_ID,
            status=TaskStatus.COMPLETED,
            due_date=date(2026, 3, 20),
            priority=TaskPriority.LOW,
        )
        Task.objects.create(
            title="Hidden company task",
            company_id=hidden_company.id,
            user_id=MANAGER_USER_ID,
            status=TaskStatus.OPEN,
            due_date=date(2026, 3, 18),
            priority=TaskPriority.HIGH,
        )

        response = self.graphql(
            """
                query FilteredTasks($filters: TaskFiltersInput) {
                    tasks(filters: $filters) {
                        id
                        title
                        status
                        userId
                        dueDate
                        priority
                        company {
                            id
                            name
                        }
                        contact {
                            id
                            name
                        }
                        deal {
                            id
                        }
                    }
                }
            """,
            variables={
                "filters": {
                    "status": "OPEN",
                    "userId": str(MANAGER_USER_ID),
                    "dueBefore": "2026-03-20",
                }
            },
            headers=self.manager_headers(visible_company.id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"]["tasks"],
            [
                {
                    "id": str(matching_task.id),
                    "title": "Call customer",
                    "status": TaskStatus.OPEN,
                    "userId": str(MANAGER_USER_ID),
                    "dueDate": "2026-03-20",
                    "priority": TaskPriority.HIGH,
                    "company": {
                        "id": str(visible_company.id),
                        "name": "Visible Co",
                    },
                    "contact": {
                        "id": str(visible_contact.id),
                        "name": "Visible Contact",
                    },
                    "deal": {
                        "id": str(matching_task.deal_id),
                    },
                }
            ],
        )

    def test_update_task_can_change_status_from_open_to_completed(self):
        company = Company.objects.create(name="Adventure Works")
        task = Task.objects.create(
            title="Confirm meeting",
            company_id=company.id,
            user_id=MANAGER_USER_ID,
            status=TaskStatus.OPEN,
            priority=TaskPriority.MEDIUM,
        )

        response = self.graphql(
            """
                mutation UpdateTask($input: UpdateTaskInput!) {
                    updateTask(input: $input) {
                        id
                        status
                    }
                }
            """,
            variables={
                "input": {
                    "taskId": str(task.id),
                    "status": "COMPLETED",
                }
            },
            headers=self.manager_headers(company.id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"]["updateTask"]["status"],
            TaskStatus.COMPLETED,
        )
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.COMPLETED)

    @patch("apps.crm.graphql.fetch_deal_reference")
    def test_create_activity_and_query_history(
        self,
        mock_fetch_deal_reference,
    ):
        company = Company.objects.create(name="Tailspin")
        contact = Contact.objects.create(
            company=company,
            name="Morgan Diaz",
            email="morgan@tailspin.test",
        )
        deal_id = str(uuid.uuid4())
        mock_fetch_deal_reference.return_value = {
            "id": deal_id,
            "companyId": str(company.id),
        }

        create_response = self.graphql(
            """
                mutation CreateActivity($input: CreateActivityInput!) {
                    createActivity(input: $input) {
                        id
                        companyId
                        contactId
                        dealId
                        userId
                        type
                        details
                        occurredAt
                        company {
                            id
                            name
                        }
                        contact {
                            id
                            name
                        }
                        deal {
                            id
                        }
                    }
                }
            """,
            variables={
                "input": {
                    "companyId": str(company.id),
                    "contactId": str(contact.id),
                    "dealId": deal_id,
                    "userId": str(MANAGER_USER_ID),
                    "type": "CALL",
                    "details": "Discussed renewal scope",
                    "occurredAt": "2026-03-15T16:00:00Z",
                }
            },
            headers=self.manager_headers(company.id),
        )

        self.assertEqual(create_response.status_code, 200)
        payload = create_response.json()["data"]["createActivity"]
        self.assertEqual(payload["companyId"], str(company.id))
        self.assertEqual(payload["contactId"], str(contact.id))
        self.assertEqual(payload["dealId"], deal_id)
        self.assertEqual(payload["type"], "CALL")
        self.assertEqual(payload["occurredAt"], "2026-03-15T16:00:00Z")
        self.assertEqual(payload["company"]["name"], "Tailspin")
        self.assertEqual(payload["contact"]["name"], "Morgan Diaz")
        self.assertEqual(payload["deal"]["id"], deal_id)

        Activity.objects.create(
            company_id=company.id,
            user_id=MANAGER_USER_ID,
            type="NOTE",
            details="Internal prep note",
            occurred_at="2026-03-14T09:00:00Z",
        )

        query_response = self.graphql(
            """
                query ActivityHistory($companyId: ID!, $contactId: ID!, $dealId: ID!) {
                    companyActivities: activities(companyId: $companyId) {
                        id
                    }
                    scopedActivities: activities(
                        companyId: $companyId
                        contactId: $contactId
                        dealId: $dealId
                    ) {
                        id
                        type
                        details
                    }
                }
            """,
            variables={
                "companyId": str(company.id),
                "contactId": str(contact.id),
                "dealId": deal_id,
            },
            headers=self.manager_headers(company.id),
        )

        self.assertEqual(query_response.status_code, 200)
        self.assertEqual(len(query_response.json()["data"]["companyActivities"]), 2)
        self.assertEqual(
            query_response.json()["data"]["scopedActivities"],
            [
                {
                    "id": payload["id"],
                    "type": "CALL",
                    "details": "Discussed renewal scope",
                }
            ],
        )

    @patch("apps.crm.graphql.fetch_deal_reference")
    def test_invalid_relationships_are_rejected_clearly(self, mock_fetch_deal_reference):
        company = Company.objects.create(name="Primary")
        other_company = Company.objects.create(name="Secondary")
        other_contact = Contact.objects.create(
            company=other_company,
            name="Avery Quinn",
            email="avery@secondary.test",
        )
        missing_company_response = self.graphql(
            """
                mutation CreateTask($input: CreateTaskInput!) {
                    createTask(input: $input) {
                        id
                    }
                }
            """,
            variables={
                "input": {
                    "title": "Missing company",
                    "companyId": str(uuid.uuid4()),
                    "userId": str(MANAGER_USER_ID),
                    "priority": "LOW",
                }
            },
            headers=self.admin_headers(),
        )

        wrong_contact_response = self.graphql(
            """
                mutation CreateTask($input: CreateTaskInput!) {
                    createTask(input: $input) {
                        id
                    }
                }
            """,
            variables={
                "input": {
                    "title": "Wrong contact",
                    "companyId": str(company.id),
                    "contactId": str(other_contact.id),
                    "userId": str(MANAGER_USER_ID),
                    "priority": "LOW",
                }
            },
            headers=self.manager_headers(company.id),
        )

        mock_fetch_deal_reference.return_value = {
            "id": str(uuid.uuid4()),
            "companyId": str(other_company.id),
        }
        wrong_deal_response = self.graphql(
            """
                mutation CreateActivity($input: CreateActivityInput!) {
                    createActivity(input: $input) {
                        id
                    }
                }
            """,
            variables={
                "input": {
                    "companyId": str(company.id),
                    "dealId": str(uuid.uuid4()),
                    "userId": str(MANAGER_USER_ID),
                    "type": "EMAIL",
                    "details": "Wrong deal",
                    "occurredAt": "2026-03-15T10:30:00Z",
                }
            },
            headers=self.manager_headers(company.id),
        )

        self.assertEqual(
            missing_company_response.json()["errors"][0]["message"],
            "Company not found.",
        )
        self.assertEqual(
            wrong_contact_response.json()["errors"][0]["message"],
            "Contact must belong to the selected company.",
        )
        self.assertEqual(
            wrong_deal_response.json()["errors"][0]["message"],
            "Deal must belong to the selected company.",
        )

    def test_kafka_generated_tasks_are_visible_through_tasks_query(self):
        company = Company.objects.create(id=DEFAULT_COMPANY_ID, name="Kafka Co")

        handle_consumer_message(
            SimpleNamespace(
                offset=12,
                partition=0,
                topic="deal.status_changed",
                value={
                    "eventId": "evt-123",
                    "eventType": "deal.status_changed",
                    "eventVersion": 1,
                    "occurredAt": "2026-03-15T15:30:00Z",
                    "dealId": "22222222-2222-2222-2222-222222222222",
                    "companyId": str(company.id),
                    "oldStatus": "NEW",
                    "newStatus": "QUALIFIED",
                },
            )
        )

        response = self.graphql(
            """
                query Tasks {
                    tasks {
                        title
                        status
                        priority
                        userId
                        dealId
                    }
                }
            """,
            headers=self.manager_headers(company.id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"]["tasks"],
            [
                {
                    "title": "Schedule follow-up",
                    "status": TaskStatus.OPEN,
                    "priority": TaskPriority.MEDIUM,
                    "userId": str(MANAGER_USER_ID),
                    "dealId": "22222222-2222-2222-2222-222222222222",
                }
            ],
        )


class DealStatusChangedConsumerTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(id=DEFAULT_COMPANY_ID, name="Kafka Co")
        self.company_id = self.company.id

    def build_message(self, *, event_id="evt-123", new_status="QUALIFIED"):
        return SimpleNamespace(
            offset=12,
            partition=0,
            topic="deal.status_changed",
            value={
                "eventId": event_id,
                "eventType": "deal.status_changed",
                "eventVersion": 1,
                "occurredAt": "2026-03-15T15:30:00Z",
                "dealId": "22222222-2222-2222-2222-222222222222",
                "companyId": str(self.company_id),
                "oldStatus": "NEW",
                "newStatus": new_status,
            },
        )

    def test_consumer_creates_follow_up_task_for_qualified_status(self):
        with self.assertLogs("apps.crm.consumer", level="INFO") as captured_logs:
            result = handle_consumer_message(self.build_message())

        self.assertEqual(result["outcome"], "task_created")
        task = Task.objects.get()
        self.assertEqual(task.title, "Schedule follow-up")
        self.assertEqual(task.company_id, self.company.id)
        self.assertEqual(
            task.deal_id,
            uuid.UUID("22222222-2222-2222-2222-222222222222"),
        )
        self.assertEqual(task.user_id, MANAGER_USER_ID)
        self.assertEqual(task.priority, TaskPriority.MEDIUM)
        self.assertEqual(task.source_event_id, "evt-123")
        log_output = "\n".join(captured_logs.output)
        self.assertIn("deal_status_changed_received", log_output)
        self.assertIn("task_created", log_output)
        self.assertIn("eventId", log_output)
        self.assertIn("dealId", log_output)
        self.assertIn("companyId", log_output)

    def test_replaying_same_event_does_not_create_duplicate_task(self):
        handle_consumer_message(self.build_message())

        with self.assertLogs("apps.crm.consumer", level="INFO") as captured_logs:
            result = handle_consumer_message(self.build_message())

        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(result["outcome"], "duplicate_ignored")
        self.assertIn("duplicate_ignored", "\n".join(captured_logs.output))

    def test_non_qualifying_status_is_logged_as_no_action(self):
        with self.assertLogs("apps.crm.consumer", level="INFO") as captured_logs:
            result = handle_consumer_message(
                self.build_message(
                    event_id="evt-456",
                    new_status="WON",
                )
            )

        self.assertEqual(result["outcome"], "no_action")
        self.assertFalse(Task.objects.exists())
        self.assertIn("no_action", "\n".join(captured_logs.output))

    def test_missing_company_is_rejected_as_invalid_event(self):
        self.company.delete()

        with self.assertRaisesMessage(
            ValueError,
            "Company not found for deal status event.",
        ):
            handle_consumer_message(self.build_message(event_id="evt-789"))
