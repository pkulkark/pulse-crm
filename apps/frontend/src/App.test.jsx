import { expect, test } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MockedProvider } from '@apollo/client/testing/react';

import { App } from './App';
import { AUTH_STORAGE_KEY } from './apollo';
import {
  ACTIVITIES_QUERY,
  COMPANY_DETAIL_QUERY,
  COMPANIES_QUERY,
  DEAL_DETAIL_QUERY,
  DEALS_QUERY,
  ME_QUERY,
  TASKS_QUERY,
} from './graphql';

const companyId = '11111111-1111-1111-1111-111111111111';
const dealId = '22222222-2222-2222-2222-222222222222';
const contactId = '33333333-3333-3333-3333-333333333333';

function createViewer(role) {
  return {
    __typename: 'User',
    companyId,
    email: `${role.toLowerCase()}@example.com`,
    id: `${role.toLowerCase()}-user`,
    name: `${role} User`,
    role,
  };
}

function createAuthenticatedMocks(role = 'ADMIN') {
  const viewer = createViewer(role);

  return [
    {
      request: { query: ME_QUERY },
      result: {
        data: {
          me: viewer,
        },
      },
    },
    {
      request: { query: COMPANIES_QUERY },
      result: {
        data: {
          companies: [
            {
              __typename: 'Company',
              contacts: [{ __typename: 'Contact', id: contactId }],
              id: companyId,
              name: 'Northwind',
              parentCompany: null,
              parentCompanyId: null,
            },
          ],
        },
      },
    },
    {
      request: {
        query: COMPANY_DETAIL_QUERY,
        variables: { id: companyId },
      },
      result: {
        data: {
          company: {
            __typename: 'Company',
            childCompanies: [],
            contacts: [
              {
                __typename: 'Contact',
                companyId,
                email: 'pat@northwind.test',
                id: contactId,
                jobTitle: 'VP Sales',
                name: 'Pat Lee',
              },
            ],
            id: companyId,
            name: 'Northwind',
            parentCompany: null,
            parentCompanyId: null,
          },
        },
      },
    },
    {
      request: {
        query: ACTIVITIES_QUERY,
        variables: {
          companyId,
          contactId: null,
          dealId: null,
        },
      },
      result: {
        data: {
          activities: [],
        },
      },
    },
    {
      request: {
        query: TASKS_QUERY,
        variables: {
          filters: {
            status: 'OPEN',
          },
        },
      },
      result: {
        data: {
          tasks: [],
        },
      },
    },
    {
      request: {
        query: DEALS_QUERY,
      },
      result: {
        data: {
          deals: [
            {
              __typename: 'Deal',
              company: {
                __typename: 'Company',
                id: companyId,
                name: 'Northwind',
              },
              companyId,
              id: dealId,
              primaryContact: {
                __typename: 'Contact',
                email: 'pat@northwind.test',
                id: contactId,
                name: 'Pat Lee',
              },
              primaryContactId: contactId,
              status: 'NEW',
            },
          ],
        },
      },
    },
    {
      request: {
        query: DEAL_DETAIL_QUERY,
        variables: { id: dealId },
      },
      result: {
        data: {
          deal: {
            __typename: 'Deal',
            company: {
              __typename: 'Company',
              id: companyId,
              name: 'Northwind',
            },
            companyId,
            id: dealId,
            primaryContact: {
              __typename: 'Contact',
              email: 'pat@northwind.test',
              id: contactId,
              name: 'Pat Lee',
            },
            primaryContactId: contactId,
            status: 'NEW',
          },
        },
      },
    },
    {
      request: {
        query: ACTIVITIES_QUERY,
        variables: {
          companyId: null,
          contactId: null,
          dealId,
        },
      },
      result: {
        data: {
          activities: [],
        },
      },
    },
    {
      request: {
        query: TASKS_QUERY,
        variables: {
          filters: {
            status: 'OPEN',
          },
        },
      },
      result: {
        data: {
          tasks: [],
        },
      },
    },
    {
      request: {
        query: TASKS_QUERY,
        variables: {
          filters: {
            status: 'OPEN',
            userId: viewer.id,
          },
        },
      },
      result: {
        data: {
          tasks: [],
        },
      },
    },
  ];
}

function renderApp(mocks) {
  return render(
    <MockedProvider addTypename mocks={mocks}>
      <App />
    </MockedProvider>,
  );
}

test('renders the login screen when no token is stored', () => {
  window.localStorage.removeItem(AUTH_STORAGE_KEY);

  renderApp([]);

  expect(
    screen.getByRole('heading', { name: 'Sign in to the workspace' }),
  ).not.toBeNull();
  expect(screen.getByLabelText('Email')).not.toBeNull();
  expect(screen.getByText(/Known sample users/i)).not.toBeNull();
});

test('returns to the login screen when the restored session has no viewer', async () => {
  window.localStorage.setItem(AUTH_STORAGE_KEY, 'stale-token');

  renderApp([
    {
      request: { query: ME_QUERY },
      result: {
        data: {
          me: null,
        },
      },
    },
  ]);

  await screen.findByRole('heading', { name: 'Sign in to the workspace' });

  expect(screen.getByText('Sign in to continue.')).not.toBeNull();
});

test('shows admin-only company and contact actions for admins', async () => {
  window.localStorage.setItem(AUTH_STORAGE_KEY, 'test-token');

  renderApp(createAuthenticatedMocks('ADMIN'));

  await screen.findByRole('heading', { name: 'Northwind' });

  expect(screen.getByRole('button', { name: 'Add Company' })).not.toBeNull();
  expect(screen.getByRole('button', { name: 'Edit company' })).not.toBeNull();
  expect(screen.getByRole('button', { name: 'Add contact' })).not.toBeNull();
});

test('hides admin-only actions for managers while leaving operational actions visible', async () => {
  window.localStorage.setItem(AUTH_STORAGE_KEY, 'test-token');

  renderApp(createAuthenticatedMocks('MANAGER'));

  await screen.findByRole('heading', { name: 'Northwind' });

  expect(screen.queryByRole('button', { name: 'Add Company' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Edit company' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Add contact' })).toBeNull();
  expect(screen.getByRole('button', { name: 'Create deal' })).not.toBeNull();
  expect(screen.getByRole('button', { name: 'Log activity' })).not.toBeNull();
});

test('navigates between main workspaces after sign-in', async () => {
  window.localStorage.setItem(AUTH_STORAGE_KEY, 'test-token');

  renderApp(createAuthenticatedMocks('MANAGER'));

  await screen.findByRole('heading', { name: 'Northwind' });

  await userEvent.click(screen.getByRole('button', { name: 'Deals' }));
  await waitFor(() => {
    expect(screen.getByRole('heading', { name: /Deal /i })).not.toBeNull();
  });

  await userEvent.click(screen.getByRole('button', { name: 'Tasks' }));
  await waitFor(() => {
    expect(screen.getByRole('heading', { name: 'Work queue' })).not.toBeNull();
  });
});

test('sign out returns to the login screen instead of rendering a blank page', async () => {
  window.localStorage.setItem(AUTH_STORAGE_KEY, 'test-token');

  renderApp(createAuthenticatedMocks('MANAGER'));

  await screen.findByRole('heading', { name: 'Northwind' });

  await userEvent.click(screen.getByRole('button', { name: 'Sign out' }));

  await screen.findByRole('heading', { name: 'Sign in to the workspace' });
  expect(screen.getByText(/Known sample users/i)).not.toBeNull();
});
