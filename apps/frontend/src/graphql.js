import { gql } from '@apollo/client';

export const LOGIN_MUTATION = gql`
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
`;

export const ME_QUERY = gql`
  query Me {
    me {
      id
      companyId
      name
      email
      role
    }
  }
`;

export const USERS_QUERY = gql`
  query Users($role: UserRole) {
    users(role: $role) {
      id
      name
      email
      role
    }
  }
`;

export const COMPANIES_QUERY = gql`
  query Companies {
    companies {
      id
      name
      parentCompanyId
      parentCompany {
        id
        name
      }
      contacts {
        id
      }
    }
  }
`;

export const COMPANY_DETAIL_QUERY = gql`
  query CompanyDetail($id: ID!) {
    company(id: $id) {
      id
      name
      parentCompanyId
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
        companyId
        name
        email
        jobTitle
      }
    }
  }
`;

export const DEALS_QUERY = gql`
  query Deals {
    deals {
      id
      companyId
      primaryContactId
      status
      company {
        id
        name
      }
      primaryContact {
        id
        name
        email
      }
    }
  }
`;

export const DEAL_DETAIL_QUERY = gql`
  query DealDetail($id: ID!) {
    deal(id: $id) {
      id
      companyId
      primaryContactId
      status
      company {
        id
        name
      }
      primaryContact {
        id
        name
        email
      }
    }
  }
`;

export const TASKS_QUERY = gql`
  query Tasks($filters: TaskFiltersInput) {
    tasks(filters: $filters) {
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
        status
      }
    }
  }
`;

export const ACTIVITIES_QUERY = gql`
  query Activities($companyId: ID, $dealId: ID, $contactId: ID) {
    activities(companyId: $companyId, dealId: $dealId, contactId: $contactId) {
      id
      companyId
      contactId
      dealId
      userId
      type
      details
      occurredAt
    }
  }
`;

export const CREATE_COMPANY_MUTATION = gql`
  mutation CreateCompany($input: CreateCompanyInput!) {
    createCompany(input: $input) {
      id
      name
      parentCompanyId
    }
  }
`;

export const UPDATE_COMPANY_MUTATION = gql`
  mutation UpdateCompany($input: UpdateCompanyInput!) {
    updateCompany(input: $input) {
      id
      name
      parentCompanyId
    }
  }
`;

export const CREATE_CONTACT_MUTATION = gql`
  mutation CreateContact($input: CreateContactInput!) {
    createContact(input: $input) {
      id
      companyId
      name
      email
      jobTitle
    }
  }
`;

export const UPDATE_CONTACT_MUTATION = gql`
  mutation UpdateContact($input: UpdateContactInput!) {
    updateContact(input: $input) {
      id
      companyId
      name
      email
      jobTitle
    }
  }
`;

export const CREATE_DEAL_MUTATION = gql`
  mutation CreateDeal($input: CreateDealInput!) {
    createDeal(input: $input) {
      id
      companyId
      primaryContactId
      status
    }
  }
`;

export const UPDATE_DEAL_STATUS_MUTATION = gql`
  mutation UpdateDealStatus($input: UpdateDealStatusInput!) {
    updateDealStatus(input: $input) {
      id
      status
    }
  }
`;

export const CREATE_TASK_MUTATION = gql`
  mutation CreateTask($input: CreateTaskInput!) {
    createTask(input: $input) {
      id
      status
      title
    }
  }
`;

export const UPDATE_TASK_MUTATION = gql`
  mutation UpdateTask($input: UpdateTaskInput!) {
    updateTask(input: $input) {
      id
      title
      status
      dueDate
      priority
    }
  }
`;

export const CREATE_ACTIVITY_MUTATION = gql`
  mutation CreateActivity($input: CreateActivityInput!) {
    createActivity(input: $input) {
      id
      type
      details
      occurredAt
    }
  }
`;
