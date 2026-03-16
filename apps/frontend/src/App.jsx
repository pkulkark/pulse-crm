import { useEffect, useState } from 'react';

import { useMutation, useQuery } from '@apollo/client/react';

import {
  AUTH_STORAGE_KEY,
  clearStoredAuthToken,
  getStoredAuthToken,
  setStoredAuthToken,
} from './apollo';
import {
  ACTIVITIES_QUERY,
  COMPANY_DETAIL_QUERY,
  COMPANIES_QUERY,
  CREATE_ACTIVITY_MUTATION,
  CREATE_COMPANY_MUTATION,
  CREATE_CONTACT_MUTATION,
  CREATE_DEAL_MUTATION,
  CREATE_TASK_MUTATION,
  DEAL_DETAIL_QUERY,
  DEALS_QUERY,
  LOGIN_MUTATION,
  ME_QUERY,
  TASKS_QUERY,
  UPDATE_COMPANY_MUTATION,
  UPDATE_CONTACT_MUTATION,
  UPDATE_DEAL_STATUS_MUTATION,
  UPDATE_TASK_MUTATION,
} from './graphql';

const DEAL_STATUSES = ['NEW', 'QUALIFIED', 'WON', 'LOST'];
const TASK_STATUSES = ['OPEN', 'COMPLETED'];
const TASK_PRIORITIES = ['LOW', 'MEDIUM', 'HIGH'];
const ACTIVITY_TYPES = ['CALL', 'EMAIL', 'MEETING', 'NOTE'];

function shortId(value) {
  if (!value) {
    return 'n/a';
  }

  return value.slice(0, 8);
}

function formatEnumLabel(value) {
  if (!value) {
    return 'Unknown';
  }

  return value
    .toLowerCase()
    .split('_')
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}

function formatDate(value) {
  if (!value) {
    return 'No due date';
  }

  return new Date(`${value}T00:00:00`).toLocaleDateString();
}

function formatDateTime(value) {
  if (!value) {
    return 'No timestamp';
  }

  return new Date(value).toLocaleString();
}

function toDatetimeLocalValue(value) {
  const date = value ? new Date(value) : new Date();
  const offset = date.getTimezoneOffset();
  const localDate = new Date(date.getTime() - offset * 60_000);
  return localDate.toISOString().slice(0, 16);
}

function toIsoDateTime(value) {
  if (!value) {
    return new Date().toISOString();
  }

  return new Date(value).toISOString();
}

function getApolloErrorMessage(error) {
  if (!error) {
    return null;
  }

  const graphQLErrors =
    error.graphQLErrors ??
    error.cause?.errors ??
    error.cause?.result?.errors ??
    [];

  const graphQLMessage = graphQLErrors.find(Boolean)?.message;
  if (graphQLMessage) {
    return graphQLMessage;
  }

  return error.message ?? 'Something went wrong.';
}

function isUnauthenticatedError(error) {
  if (!error) {
    return false;
  }

  const graphQLErrors =
    error.graphQLErrors ??
    error.cause?.errors ??
    error.cause?.result?.errors ??
    [];

  if (
    graphQLErrors.some(
      (entry) => entry?.extensions?.code === 'UNAUTHENTICATED',
    )
  ) {
    return true;
  }

  const statusCode =
    error.networkError?.statusCode ??
    error.cause?.statusCode ??
    error.statusCode;

  return statusCode === 401;
}

function buildTaskFilters({ scope, status, userId }) {
  const filters = {};

  if (scope === 'mine') {
    filters.userId = userId;
  }

  if (status !== 'ALL') {
    filters.status = status;
  }

  return Object.keys(filters).length > 0 ? filters : null;
}

function sortNewestFirst(left, right) {
  return new Date(right).getTime() - new Date(left).getTime();
}

function filterCompanies(companies, search, relationship) {
  const normalizedSearch = search.trim().toLowerCase();

  return companies.filter((company) => {
    const matchesSearch =
      normalizedSearch.length === 0 ||
      company.name.toLowerCase().includes(normalizedSearch) ||
      company.parentCompany?.name?.toLowerCase().includes(normalizedSearch);

    if (!matchesSearch) {
      return false;
    }

    if (relationship === 'parents') {
      return !company.parentCompanyId;
    }

    if (relationship === 'children') {
      return Boolean(company.parentCompanyId);
    }

    return true;
  });
}

function filterDeals(deals, search, status) {
  const normalizedSearch = search.trim().toLowerCase();

  return deals.filter((deal) => {
    const matchesStatus = status === 'ALL' || deal.status === status;
    const searchableText = [
      `deal ${shortId(deal.id)}`,
      deal.company?.name ?? '',
      deal.primaryContact?.name ?? '',
    ]
      .join(' ')
      .toLowerCase();

    const matchesSearch =
      normalizedSearch.length === 0 ||
      searchableText.includes(normalizedSearch);

    return matchesStatus && matchesSearch;
  });
}

function LoginScreen({ message, onLoggedIn }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [formError, setFormError] = useState('');
  const [login, { loading }] = useMutation(LOGIN_MUTATION);

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError('');

    try {
      const { data } = await login({
        variables: {
          input: {
            email,
            password,
          },
        },
      });

      onLoggedIn(data.login.token);
    } catch (error) {
      setFormError(getApolloErrorMessage(error));
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <p className="eyebrow">PulseCRM</p>
        <h1>Sign in to the workspace</h1>

        <div className="auth-hint">
          <p>Known sample users</p>
          <p>`admin@example.com` / `secret`</p>
          <p>`manager@example.com` / `secret`</p>
        </div>

        {message ? <InlineMessage tone="info">{message}</InlineMessage> : null}
        {formError ? <InlineMessage tone="error">{formError}</InlineMessage> : null}

        <form className="stacked-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Email</span>
            <input
              autoComplete="username"
              name="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              autoComplete="current-password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          <button className="primary-button" disabled={loading} type="submit">
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
  );
}

function CompanyFormDialog({
  companies,
  initialCompany,
  onClose,
  onSaved,
  open,
}) {
  const [name, setName] = useState('');
  const [parentCompanyId, setParentCompanyId] = useState('');
  const [formError, setFormError] = useState('');
  const [createCompany, createState] = useMutation(CREATE_COMPANY_MUTATION);
  const [updateCompany, updateState] = useMutation(UPDATE_COMPANY_MUTATION);
  const isEditing = Boolean(initialCompany);
  const loading = createState.loading || updateState.loading;

  useEffect(() => {
    if (!open) {
      return;
    }

    setName(initialCompany?.name ?? '');
    setParentCompanyId(initialCompany?.parentCompanyId ?? '');
    setFormError('');
  }, [initialCompany, open]);

  if (!open) {
    return null;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError('');

    try {
      const result = isEditing
        ? await updateCompany({
            variables: {
              input: {
                companyId: initialCompany.id,
                name,
                parentCompanyId: parentCompanyId || null,
              },
            },
          })
        : await createCompany({
            variables: {
              input: {
                name,
                parentCompanyId: parentCompanyId || null,
              },
            },
          });

      onSaved(result.data[isEditing ? 'updateCompany' : 'createCompany']);
    } catch (error) {
      setFormError(getApolloErrorMessage(error));
    }
  }

  const availableParents = companies.filter(
    (company) => company.id !== initialCompany?.id,
  );

  return (
    <Dialog
      title={isEditing ? 'Edit company' : 'New company'}
      subtitle="Keep the record small: company name plus optional parent."
      onClose={onClose}
    >
      {formError ? <InlineMessage tone="error">{formError}</InlineMessage> : null}
      <form className="stacked-form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Company name</span>
          <input
            onChange={(event) => setName(event.target.value)}
            required
            value={name}
          />
        </label>

        <label className="field">
          <span>Parent company</span>
          <select
            onChange={(event) => setParentCompanyId(event.target.value)}
            value={parentCompanyId}
          >
            <option value="">No parent company</option>
            {availableParents.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
        </label>

        <div className="dialog-actions">
          <button className="secondary-button" onClick={onClose} type="button">
            Cancel
          </button>
          <button className="primary-button" disabled={loading} type="submit">
            {loading ? 'Saving…' : isEditing ? 'Update company' : 'Create company'}
          </button>
        </div>
      </form>
    </Dialog>
  );
}

function ContactFormDialog({
  company,
  initialContact,
  onClose,
  onSaved,
  open,
}) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [formError, setFormError] = useState('');
  const [createContact, createState] = useMutation(CREATE_CONTACT_MUTATION);
  const [updateContact, updateState] = useMutation(UPDATE_CONTACT_MUTATION);
  const isEditing = Boolean(initialContact);
  const loading = createState.loading || updateState.loading;

  useEffect(() => {
    if (!open) {
      return;
    }

    setName(initialContact?.name ?? '');
    setEmail(initialContact?.email ?? '');
    setJobTitle(initialContact?.jobTitle ?? '');
    setFormError('');
  }, [initialContact, open]);

  if (!open || !company) {
    return null;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError('');

    try {
      await (isEditing
        ? updateContact({
            variables: {
              input: {
                contactId: initialContact.id,
                email,
                jobTitle,
                name,
              },
            },
          })
        : createContact({
            variables: {
              input: {
                companyId: company.id,
                email,
                jobTitle,
                name,
              },
            },
          }));

      onSaved();
    } catch (error) {
      setFormError(getApolloErrorMessage(error));
    }
  }

  return (
    <Dialog
      title={isEditing ? 'Edit contact' : 'New contact'}
      subtitle={`Company: ${company.name}`}
      onClose={onClose}
    >
      {formError ? <InlineMessage tone="error">{formError}</InlineMessage> : null}
      <form className="stacked-form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Name</span>
          <input
            onChange={(event) => setName(event.target.value)}
            required
            value={name}
          />
        </label>

        <label className="field">
          <span>Email</span>
          <input
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
        </label>

        <label className="field">
          <span>Job title</span>
          <input
            onChange={(event) => setJobTitle(event.target.value)}
            value={jobTitle}
          />
        </label>

        <div className="dialog-actions">
          <button className="secondary-button" onClick={onClose} type="button">
            Cancel
          </button>
          <button className="primary-button" disabled={loading} type="submit">
            {loading ? 'Saving…' : isEditing ? 'Update contact' : 'Create contact'}
          </button>
        </div>
      </form>
    </Dialog>
  );
}

function DealFormDialog({
  companies,
  initialCompanyId,
  onClose,
  onSaved,
  open,
}) {
  const [companyId, setCompanyId] = useState('');
  const [primaryContactId, setPrimaryContactId] = useState('');
  const [status, setStatus] = useState('NEW');
  const [formError, setFormError] = useState('');
  const [createDeal, { loading }] = useMutation(CREATE_DEAL_MUTATION);
  const companyQuery = useQuery(COMPANY_DETAIL_QUERY, {
    skip: !open || !companyId,
    variables: { id: companyId },
  });

  useEffect(() => {
    if (!open) {
      return;
    }

    setCompanyId(initialCompanyId ?? companies[0]?.id ?? '');
    setPrimaryContactId('');
    setStatus('NEW');
    setFormError('');
  }, [companies, initialCompanyId, open]);

  useEffect(() => {
    setPrimaryContactId('');
  }, [companyId]);

  if (!open) {
    return null;
  }

  const contacts = companyQuery.data?.company?.contacts ?? [];

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError('');

    try {
      const { data } = await createDeal({
        variables: {
          input: {
            companyId,
            primaryContactId: primaryContactId || null,
            status,
          },
        },
      });

      onSaved(data.createDeal);
    } catch (error) {
      setFormError(getApolloErrorMessage(error));
    }
  }

  return (
    <Dialog
      title="New deal"
      subtitle="Attach the deal to one company and optionally to one primary contact."
      onClose={onClose}
    >
      {formError ? <InlineMessage tone="error">{formError}</InlineMessage> : null}
      <form className="stacked-form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Company</span>
          <select
            onChange={(event) => setCompanyId(event.target.value)}
            required
            value={companyId}
          >
            <option value="" disabled>
              Select a company
            </option>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Primary contact</span>
          <select
            onChange={(event) => setPrimaryContactId(event.target.value)}
            value={primaryContactId}
          >
            <option value="">No primary contact</option>
            {contacts.map((contact) => (
              <option key={contact.id} value={contact.id}>
                {contact.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Initial status</span>
          <select
            onChange={(event) => setStatus(event.target.value)}
            value={status}
          >
            {DEAL_STATUSES.map((entry) => (
              <option key={entry} value={entry}>
                {formatEnumLabel(entry)}
              </option>
            ))}
          </select>
        </label>

        <div className="dialog-actions">
          <button className="secondary-button" onClick={onClose} type="button">
            Cancel
          </button>
          <button className="primary-button" disabled={loading} type="submit">
            {loading ? 'Saving…' : 'Create deal'}
          </button>
        </div>
      </form>
    </Dialog>
  );
}

function TaskFormDialog({
  companies,
  deals,
  initialTask,
  initialValues,
  onClose,
  onSaved,
  open,
  viewer,
}) {
  const [title, setTitle] = useState('');
  const [companyId, setCompanyId] = useState('');
  const [contactId, setContactId] = useState('');
  const [dealId, setDealId] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [priority, setPriority] = useState('MEDIUM');
  const [formError, setFormError] = useState('');
  const [createTask, createState] = useMutation(CREATE_TASK_MUTATION);
  const [updateTask, updateState] = useMutation(UPDATE_TASK_MUTATION);
  const isEditing = Boolean(initialTask);
  const loading = createState.loading || updateState.loading;
  const companyQuery = useQuery(COMPANY_DETAIL_QUERY, {
    skip: !open || !companyId,
    variables: { id: companyId },
  });

  useEffect(() => {
    if (!open) {
      return;
    }

    setTitle(initialTask?.title ?? initialValues?.title ?? '');
    setCompanyId(initialTask?.companyId ?? initialValues?.companyId ?? '');
    setContactId(initialTask?.contactId ?? initialValues?.contactId ?? '');
    setDealId(initialTask?.dealId ?? initialValues?.dealId ?? '');
    setDueDate(initialTask?.dueDate ?? initialValues?.dueDate ?? '');
    setPriority(initialTask?.priority ?? initialValues?.priority ?? 'MEDIUM');
    setFormError('');
  }, [initialTask, initialValues, open]);

  const contacts = companyQuery.data?.company?.contacts ?? [];
  const relatedDeals = deals.filter((deal) => deal.companyId === companyId);

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError('');

    try {
      await (isEditing
        ? updateTask({
            variables: {
              input: {
                dueDate: dueDate || null,
                priority,
                taskId: initialTask.id,
                title,
              },
            },
          })
        : createTask({
            variables: {
              input: {
                companyId,
                contactId: contactId || null,
                dealId: dealId || null,
                dueDate: dueDate || null,
                priority,
                title,
                userId: viewer.id,
              },
            },
          }));

      onSaved();
    } catch (error) {
      setFormError(getApolloErrorMessage(error));
    }
  }

  if (!open) {
    return null;
  }

  return (
    <Dialog
      title={isEditing ? 'Edit task' : 'New task'}
      subtitle={isEditing ? 'Update the task details.' : 'Assign the task to your current user.'}
      onClose={onClose}
    >
      {formError ? <InlineMessage tone="error">{formError}</InlineMessage> : null}
      <form className="stacked-form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Title</span>
          <input
            onChange={(event) => setTitle(event.target.value)}
            required
            value={title}
          />
        </label>

        <label className="field">
          <span>Company</span>
          <select
            disabled={isEditing}
            onChange={(event) => {
              setCompanyId(event.target.value);
              setContactId('');
              setDealId('');
            }}
            required
            value={companyId}
          >
            <option value="" disabled>
              Select a company
            </option>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Contact</span>
          <select
            onChange={(event) => setContactId(event.target.value)}
            value={contactId}
          >
            <option value="">No contact</option>
            {contacts.map((contact) => (
              <option key={contact.id} value={contact.id}>
                {contact.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Deal</span>
          <select onChange={(event) => setDealId(event.target.value)} value={dealId}>
            <option value="">No deal</option>
            {relatedDeals.map((deal) => (
              <option key={deal.id} value={deal.id}>
                Deal {shortId(deal.id)} · {formatEnumLabel(deal.status)}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Due date</span>
          <input
            onChange={(event) => setDueDate(event.target.value)}
            type="date"
            value={dueDate}
          />
        </label>

        <label className="field">
          <span>Priority</span>
          <select
            onChange={(event) => setPriority(event.target.value)}
            value={priority}
          >
            {TASK_PRIORITIES.map((entry) => (
              <option key={entry} value={entry}>
                {formatEnumLabel(entry)}
              </option>
            ))}
          </select>
        </label>

        <div className="dialog-actions">
          <button className="secondary-button" onClick={onClose} type="button">
            Cancel
          </button>
          <button className="primary-button" disabled={loading} type="submit">
            {loading ? 'Saving…' : isEditing ? 'Update task' : 'Create task'}
          </button>
        </div>
      </form>
    </Dialog>
  );
}

function ActivityFormDialog({
  companies,
  deals,
  initialValues,
  onClose,
  onSaved,
  open,
  viewer,
}) {
  const [companyId, setCompanyId] = useState('');
  const [contactId, setContactId] = useState('');
  const [dealId, setDealId] = useState('');
  const [type, setType] = useState('CALL');
  const [details, setDetails] = useState('');
  const [occurredAt, setOccurredAt] = useState(toDatetimeLocalValue());
  const [formError, setFormError] = useState('');
  const [createActivity, { loading }] = useMutation(CREATE_ACTIVITY_MUTATION);
  const companyQuery = useQuery(COMPANY_DETAIL_QUERY, {
    skip: !open || !companyId,
    variables: { id: companyId },
  });

  useEffect(() => {
    if (!open) {
      return;
    }

    setCompanyId(initialValues?.companyId ?? '');
    setContactId(initialValues?.contactId ?? '');
    setDealId(initialValues?.dealId ?? '');
    setType(initialValues?.type ?? 'CALL');
    setDetails(initialValues?.details ?? '');
    setOccurredAt(toDatetimeLocalValue(initialValues?.occurredAt));
    setFormError('');
  }, [initialValues, open]);

  const contacts = companyQuery.data?.company?.contacts ?? [];
  const relatedDeals = deals.filter((deal) => deal.companyId === companyId);

  if (!open) {
    return null;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError('');

    try {
      await createActivity({
        variables: {
          input: {
            companyId,
            contactId: contactId || null,
            dealId: dealId || null,
            details,
            occurredAt: toIsoDateTime(occurredAt),
            type,
            userId: viewer.id,
          },
        },
      });

      onSaved();
    } catch (error) {
      setFormError(getApolloErrorMessage(error));
    }
  }

  return (
    <Dialog
      title="Log activity"
      subtitle="Capture a completed interaction for the current company context."
      onClose={onClose}
    >
      {formError ? <InlineMessage tone="error">{formError}</InlineMessage> : null}
      <form className="stacked-form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Company</span>
          <select
            onChange={(event) => {
              setCompanyId(event.target.value);
              setContactId('');
              setDealId('');
            }}
            required
            value={companyId}
          >
            <option value="" disabled>
              Select a company
            </option>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Contact</span>
          <select
            onChange={(event) => setContactId(event.target.value)}
            value={contactId}
          >
            <option value="">No contact</option>
            {contacts.map((contact) => (
              <option key={contact.id} value={contact.id}>
                {contact.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Deal</span>
          <select onChange={(event) => setDealId(event.target.value)} value={dealId}>
            <option value="">No deal</option>
            {relatedDeals.map((deal) => (
              <option key={deal.id} value={deal.id}>
                Deal {shortId(deal.id)} · {formatEnumLabel(deal.status)}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Activity type</span>
          <select onChange={(event) => setType(event.target.value)} value={type}>
            {ACTIVITY_TYPES.map((entry) => (
              <option key={entry} value={entry}>
                {formatEnumLabel(entry)}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Details</span>
          <textarea
            onChange={(event) => setDetails(event.target.value)}
            required
            rows="4"
            value={details}
          />
        </label>

        <label className="field">
          <span>Occurred at</span>
          <input
            onChange={(event) => setOccurredAt(event.target.value)}
            required
            type="datetime-local"
            value={occurredAt}
          />
        </label>

        <div className="dialog-actions">
          <button className="secondary-button" onClick={onClose} type="button">
            Cancel
          </button>
          <button className="primary-button" disabled={loading} type="submit">
            {loading ? 'Saving…' : 'Create activity'}
          </button>
        </div>
      </form>
    </Dialog>
  );
}

function CompanyWorkspace({
  companies,
  companyActivities,
  companyDetail,
  companyError,
  companyLoading,
  companySearch,
  onActivityRequested,
  onCompanySearchChange,
  onCompanySelected,
  onContactCreated,
  onContactEdited,
  onCreateCompany,
  onCreateDeal,
  onCreateTask,
  onEditCompany,
  onRelationshipFilterChange,
  onRetry,
  relationshipFilter,
  selectedCompanyId,
  tasks,
  viewer,
}) {
  const filteredCompanies = filterCompanies(
    companies,
    companySearch,
    relationshipFilter,
  );
  const isAdmin = viewer.role === 'ADMIN';

  return (
    <section className="workspace-grid">
      <article className="panel">
        <div className="panel-header">
          <div>
            <p className="panel-eyebrow">Companies</p>
            <h2>Relationship map</h2>
          </div>
          {isAdmin ? (
            <button className="primary-button" onClick={onCreateCompany} type="button">
              Add Company
            </button>
          ) : null}
        </div>

        <div className="toolbar">
          <label className="field compact-field">
            <span>Search</span>
            <input
              onChange={(event) => onCompanySearchChange(event.target.value)}
              placeholder="Search company or parent"
              value={companySearch}
            />
          </label>

          <label className="field compact-field">
            <span>Filter</span>
            <select
              onChange={(event) => onRelationshipFilterChange(event.target.value)}
              value={relationshipFilter}
            >
              <option value="all">All companies</option>
              <option value="parents">Parents only</option>
              <option value="children">Children only</option>
            </select>
          </label>
        </div>

        {companyError ? (
          <ErrorState
            actionLabel="Retry companies"
            message={getApolloErrorMessage(companyError)}
            onAction={onRetry}
          />
        ) : null}

        {!companyError && companyLoading ? <LoadingState label="Loading companies" /> : null}

        {!companyError && !companyLoading && filteredCompanies.length === 0 ? (
          <EmptyState
            body="Create the first company or widen the list filter."
            title="No companies match this view"
          />
        ) : null}

        {!companyError && filteredCompanies.length > 0 ? (
          <ul className="record-list">
            {filteredCompanies.map((company) => (
              <li key={company.id}>
                <button
                  className={
                    selectedCompanyId === company.id
                      ? 'record-button is-selected'
                      : 'record-button'
                  }
                  onClick={() => onCompanySelected(company.id)}
                  type="button"
                >
                  <span className="record-copy">
                    <strong>{company.name}</strong>
                    {company.parentCompany ? (
                      <small>Child of {company.parentCompany.name}</small>
                    ) : (
                      <small>Top-level company</small>
                    )}
                  </span>
                  <span className="pill">{company.contacts.length} contacts</span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </article>

      <article className="panel detail-panel">
        {!selectedCompanyId ? (
          <EmptyState
            body="Pick a company from the list to see contacts, tasks, deals, and activities in one place."
            title="No company selected"
          />
        ) : null}

        {selectedCompanyId && companyLoading ? (
          <LoadingState label="Loading company details" />
        ) : null}

        {selectedCompanyId && companyError ? (
          <ErrorState
            actionLabel="Retry company detail"
            message={getApolloErrorMessage(companyError)}
            onAction={onRetry}
          />
        ) : null}

        {companyDetail ? (
          <>
            <div className="panel-header">
              <div>
                <p className="panel-eyebrow">Company detail</p>
                <h2>{companyDetail.name}</h2>
                <p className="subtle-copy">
                  {companyDetail.parentCompany
                    ? `Child company under ${companyDetail.parentCompany.name}`
                    : 'Top-level company'}
                </p>
              </div>

              <div className="button-row">
                {isAdmin ? (
                  <button className="secondary-button" onClick={onEditCompany} type="button">
                    Edit company
                  </button>
                ) : (
                  <span className="permission-hint">Company edits are admin-only.</span>
                )}
                <button className="secondary-button" onClick={onCreateDeal} type="button">
                  Create deal
                </button>
                <button className="secondary-button" onClick={onCreateTask} type="button">
                  Create task
                </button>
                <button className="secondary-button" onClick={onActivityRequested} type="button">
                  Log activity
                </button>
              </div>
            </div>

            <div className="summary-grid">
              <MetricCard
                label="Child companies"
                value={String(companyDetail.childCompanies.length)}
              />
              <MetricCard
                label="Contacts"
                value={String(companyDetail.contacts.length)}
              />
              <MetricCard
                label="Open tasks"
                value={String(tasks.length)}
              />
              <MetricCard
                label="Recent activities"
                value={String(companyActivities.length)}
              />
            </div>

            <div className="detail-columns">
              <section className="subpanel">
                <div className="subpanel-header">
                  <h3>Contacts</h3>
                  {isAdmin ? (
                    <button
                      className="text-button"
                      onClick={onContactCreated}
                      type="button"
                    >
                      Add contact
                    </button>
                  ) : null}
                </div>

                {companyDetail.contacts.length === 0 ? (
                  <EmptyState
                    body="Add a contact so deals, tasks, and activity records can attach to a person."
                    title="No contacts yet"
                  />
                ) : (
                  <ul className="stack-list">
                    {companyDetail.contacts.map((contact) => (
                      <li key={contact.id} className="stack-card">
                        <div>
                          <strong>{contact.name}</strong>
                          <p>{contact.email}</p>
                          <small>{contact.jobTitle || 'No job title'}</small>
                        </div>
                        {isAdmin ? (
                          <button
                            className="text-button"
                            onClick={() => onContactEdited(contact)}
                            type="button"
                          >
                            Edit
                          </button>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="subpanel">
                <div className="subpanel-header">
                  <h3>Open tasks</h3>
                </div>

                {tasks.length === 0 ? (
                  <EmptyState
                    body="Tasks created manually or by the async workflow will show up here."
                    title="No open tasks for this company"
                  />
                ) : (
                  <ul className="stack-list">
                    {tasks.map((task) => (
                      <li key={task.id} className="stack-card">
                        <div>
                          <strong>{task.title}</strong>
                          <p>{formatEnumLabel(task.priority)} priority</p>
                          <small>
                            {task.contact?.name ?? 'No contact'} · {formatDate(task.dueDate)}
                          </small>
                        </div>
                        <span className="pill">{formatEnumLabel(task.status)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="subpanel">
                <div className="subpanel-header">
                  <h3>Recent activity</h3>
                </div>

                {companyActivities.length === 0 ? (
                  <EmptyState
                    body="Log calls, meetings, emails, and notes from this company page."
                    title="No activity yet"
                  />
                ) : (
                  <ul className="stack-list">
                    {companyActivities.map((activity) => (
                      <li key={activity.id} className="stack-card">
                        <div>
                          <strong>{formatEnumLabel(activity.type)}</strong>
                          <p>{activity.details}</p>
                          <small>{formatDateTime(activity.occurredAt)}</small>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="subpanel">
                <div className="subpanel-header">
                  <h3>Deals</h3>
                </div>

                {companyDetail.deals.length === 0 ? (
                  <EmptyState
                    body="Create the first deal from this company detail page."
                    title="No deals yet"
                  />
                ) : (
                  <ul className="stack-list">
                    {companyDetail.deals.map((deal) => (
                      <li key={deal.id} className="stack-card">
                        <div>
                          <strong>Deal {shortId(deal.id)}</strong>
                          <p>{formatEnumLabel(deal.status)}</p>
                          <small>{deal.primaryContact?.name ?? 'No primary contact'}</small>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          </>
        ) : null}
      </article>
    </section>
  );
}

function DealsWorkspace({
  dealActivities,
  dealDetail,
  dealDetailError,
  dealDetailLoading,
  dealSearch,
  deals,
  dealsError,
  dealsLoading,
  onActivityRequested,
  onCreateDeal,
  onCreateTask,
  onDealSearchChange,
  onDealSelected,
  onRetryDealDetail,
  onRetryDeals,
  onStatusFilterChange,
  onStatusUpdated,
  selectedDealId,
  statusFilter,
  tasks,
  updateState,
}) {
  const filteredDeals = filterDeals(deals, dealSearch, statusFilter);

  return (
    <section className="workspace-grid">
      <article className="panel">
        <div className="panel-header">
          <div>
            <p className="panel-eyebrow">Deals</p>
            <h2>Pipeline</h2>
          </div>
          <button className="primary-button" onClick={onCreateDeal} type="button">
            Add Deal
          </button>
        </div>

        <div className="toolbar">
          <label className="field compact-field">
            <span>Search</span>
            <input
              onChange={(event) => onDealSearchChange(event.target.value)}
              placeholder="Search deal, company, or contact"
              value={dealSearch}
            />
          </label>

          <label className="field compact-field">
            <span>Status</span>
            <select
              onChange={(event) => onStatusFilterChange(event.target.value)}
              value={statusFilter}
            >
              <option value="ALL">All statuses</option>
              {DEAL_STATUSES.map((entry) => (
                <option key={entry} value={entry}>
                  {formatEnumLabel(entry)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {dealsError ? (
          <ErrorState
            actionLabel="Retry deals"
            message={getApolloErrorMessage(dealsError)}
            onAction={onRetryDeals}
          />
        ) : null}

        {!dealsError && dealsLoading ? <LoadingState label="Loading deals" /> : null}

        {!dealsError && !dealsLoading && filteredDeals.length === 0 ? (
          <EmptyState
            body="Create a deal or change the filters."
            title="No deals in this view"
          />
        ) : null}

        {!dealsError && filteredDeals.length > 0 ? (
          <ul className="record-list">
            {filteredDeals.map((deal) => (
              <li key={deal.id}>
                <button
                  className={
                    selectedDealId === deal.id
                      ? 'record-button is-selected'
                      : 'record-button'
                  }
                  onClick={() => onDealSelected(deal.id)}
                  type="button"
                >
                  <span className="record-copy">
                    <strong>Deal {shortId(deal.id)}</strong>
                    <small>
                      {deal.company?.name ?? 'Unknown company'} ·{' '}
                      {deal.primaryContact?.name ?? 'No primary contact'}
                    </small>
                  </span>
                  <span className="pill">{formatEnumLabel(deal.status)}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </article>

      <article className="panel detail-panel">
        {!selectedDealId ? (
          <EmptyState
            body="Select a deal to update its status and watch follow-up tasks appear."
            title="No deal selected"
          />
        ) : null}

        {selectedDealId && dealDetailLoading ? <LoadingState label="Loading deal detail" /> : null}

        {selectedDealId && dealDetailError ? (
          <ErrorState
            actionLabel="Retry deal detail"
            message={getApolloErrorMessage(dealDetailError)}
            onAction={onRetryDealDetail}
          />
        ) : null}

        {dealDetail ? (
          <>
            <div className="panel-header">
              <div>
                <p className="panel-eyebrow">Deal detail</p>
                <h2>Deal {shortId(dealDetail.id)}</h2>
                <p className="subtle-copy">
                  {dealDetail.company?.name ?? 'Unknown company'} ·{' '}
                  {dealDetail.primaryContact?.name ?? 'No primary contact'}
                </p>
              </div>

              <div className="button-row">
                <button className="secondary-button" onClick={onCreateTask} type="button">
                  Create task
                </button>
                <button className="secondary-button" onClick={onActivityRequested} type="button">
                  Log activity
                </button>
              </div>
            </div>

            {updateState.statusNotice ? (
              <InlineMessage tone="info">{updateState.statusNotice}</InlineMessage>
            ) : null}
            {updateState.error ? (
              <InlineMessage tone="error">
                {getApolloErrorMessage(updateState.error)}
              </InlineMessage>
            ) : null}

            <div className="summary-grid">
              <MetricCard label="Current status" value={formatEnumLabel(dealDetail.status)} />
              <MetricCard label="Open deal tasks" value={String(tasks.length)} />
              <MetricCard label="Related activities" value={String(dealActivities.length)} />
            </div>

            <section className="subpanel deal-status-panel">
              <div className="subpanel-header">
                <h3>Update status</h3>
              </div>
              <div className="button-row">
                {DEAL_STATUSES.map((entry) => (
                  <button
                    key={entry}
                    className={
                      entry === dealDetail.status ? 'status-button is-active' : 'status-button'
                    }
                    disabled={updateState.loading}
                    onClick={() => onStatusUpdated(entry)}
                    type="button"
                  >
                    {formatEnumLabel(entry)}
                  </button>
                ))}
              </div>
              <p className="subtle-copy">
                Status changes update the deal immediately. Follow-up tasks may appear a few
                seconds later while the Kafka workflow completes.
              </p>
            </section>

            <div className="detail-columns">
              <section className="subpanel">
                <div className="subpanel-header">
                  <h3>Open tasks</h3>
                </div>
                {tasks.length === 0 ? (
                  <EmptyState
                    body="Tasks created for this deal will show up here."
                    title="No tasks linked to this deal"
                  />
                ) : (
                  <ul className="stack-list">
                    {tasks.map((task) => (
                      <li key={task.id} className="stack-card">
                        <div>
                          <strong>{task.title}</strong>
                          <p>{formatEnumLabel(task.priority)} priority</p>
                          <small>{formatDate(task.dueDate)}</small>
                        </div>
                        <span className="pill">{formatEnumLabel(task.status)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="subpanel">
                <div className="subpanel-header">
                  <h3>Recent activity</h3>
                </div>
                {dealActivities.length === 0 ? (
                  <EmptyState
                    body="Log calls, emails, meetings, or notes from the deal detail page."
                    title="No deal activity yet"
                  />
                ) : (
                  <ul className="stack-list">
                    {dealActivities.map((activity) => (
                      <li key={activity.id} className="stack-card">
                        <div>
                          <strong>{formatEnumLabel(activity.type)}</strong>
                          <p>{activity.details}</p>
                          <small>{formatDateTime(activity.occurredAt)}</small>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          </>
        ) : null}
      </article>
    </section>
  );
}

function TasksWorkspace({
  onCreateTask,
  onEditTask,
  onRetry,
  onScopeChange,
  onStatusChange,
  onTaskCompleted,
  scope,
  status,
  tasks,
  tasksError,
  tasksLoading,
  viewer,
}) {
  return (
    <section className="workspace-grid single-column">
      <article className="panel">
        <div className="panel-header">
          <div>
            <p className="panel-eyebrow">Tasks</p>
            <h2>Work queue</h2>
          </div>
          <button className="primary-button" onClick={onCreateTask} type="button">
            Add Task
          </button>
        </div>

        <div className="toolbar">
          <label className="field compact-field">
            <span>Status</span>
            <select onChange={(event) => onStatusChange(event.target.value)} value={status}>
              <option value="ALL">All statuses</option>
              {TASK_STATUSES.map((entry) => (
                <option key={entry} value={entry}>
                  {formatEnumLabel(entry)}
                </option>
              ))}
            </select>
          </label>

          <label className="field compact-field">
            <span>Scope</span>
            <select onChange={(event) => onScopeChange(event.target.value)} value={scope}>
              <option value="all">Visible tasks</option>
              <option value="mine">Assigned to me</option>
            </select>
          </label>
        </div>

        {tasksError ? (
          <ErrorState
            actionLabel="Retry tasks"
            message={getApolloErrorMessage(tasksError)}
            onAction={onRetry}
          />
        ) : null}

        {!tasksError && tasksLoading ? <LoadingState label="Loading tasks" /> : null}

        {!tasksError && !tasksLoading && tasks.length === 0 ? (
          <EmptyState
            body="Create a task manually or update a deal status so the async workflow can create one."
            title="No tasks in this view"
          />
        ) : null}

        {!tasksError && tasks.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Company</th>
                  <th>Context</th>
                  <th>Assignee</th>
                  <th>Due</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.id}>
                    <td>{task.title}</td>
                    <td>{task.company?.name ?? 'Unknown company'}</td>
                    <td>
                      {task.contact?.name ?? 'No contact'}
                      <br />
                      <small>{task.deal ? `Deal ${shortId(task.deal.id)}` : 'No deal'}</small>
                    </td>
                    <td>{task.userId === viewer.id ? 'You' : shortId(task.userId)}</td>
                    <td>{formatDate(task.dueDate)}</td>
                    <td>{formatEnumLabel(task.priority)}</td>
                    <td>{formatEnumLabel(task.status)}</td>
                    <td>
                      <div className="button-row compact-row">
                        <button
                          className="text-button"
                          onClick={() => onEditTask(task)}
                          type="button"
                        >
                          Edit
                        </button>
                        {task.status === 'OPEN' ? (
                          <button
                            className="text-button"
                            onClick={() => onTaskCompleted(task.id)}
                            type="button"
                          >
                            Complete
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </article>
    </section>
  );
}

function CrmWorkspace({ viewer, onLoggedOut }) {
  const [currentView, setCurrentView] = useState('companies');
  const [companySearch, setCompanySearch] = useState('');
  const [relationshipFilter, setRelationshipFilter] = useState('all');
  const [selectedCompanyId, setSelectedCompanyId] = useState(null);
  const [dealSearch, setDealSearch] = useState('');
  const [dealStatusFilter, setDealStatusFilter] = useState('ALL');
  const [selectedDealId, setSelectedDealId] = useState(null);
  const [taskStatusFilter, setTaskStatusFilter] = useState('OPEN');
  const [taskScope, setTaskScope] = useState('mine');
  const [companyDialog, setCompanyDialog] = useState(null);
  const [contactDialog, setContactDialog] = useState(null);
  const [dealDialog, setDealDialog] = useState(false);
  const [taskDialog, setTaskDialog] = useState(null);
  const [activityDialog, setActivityDialog] = useState(null);
  const [dealStatusNotice, setDealStatusNotice] = useState('');
  const [dealStatusError, setDealStatusError] = useState(null);
  const [pollDealTasks, setPollDealTasks] = useState(false);
  const companiesResult = useQuery(COMPANIES_QUERY);
  const dealsResult = useQuery(DEALS_QUERY);
  const tasksResult = useQuery(TASKS_QUERY, {
    skip: currentView !== 'tasks',
    variables: {
      filters: buildTaskFilters({
        scope: taskScope,
        status: taskStatusFilter,
        userId: viewer.id,
      }),
    },
  });
  const companyDetailResult = useQuery(COMPANY_DETAIL_QUERY, {
    skip: currentView !== 'companies' || !selectedCompanyId,
    variables: { id: selectedCompanyId },
  });
  const companyActivitiesResult = useQuery(ACTIVITIES_QUERY, {
    skip: currentView !== 'companies' || !selectedCompanyId,
    variables: { companyId: selectedCompanyId, contactId: null, dealId: null },
  });
  const companyOpenTasksResult = useQuery(TASKS_QUERY, {
    skip: currentView !== 'companies' || !selectedCompanyId,
    variables: { filters: { status: 'OPEN' } },
  });
  const dealDetailResult = useQuery(DEAL_DETAIL_QUERY, {
    skip: currentView !== 'deals' || !selectedDealId,
    variables: { id: selectedDealId },
  });
  const dealActivitiesResult = useQuery(ACTIVITIES_QUERY, {
    skip: currentView !== 'deals' || !selectedDealId,
    variables: { companyId: null, contactId: null, dealId: selectedDealId },
  });
  const dealOpenTasksResult = useQuery(TASKS_QUERY, {
    notifyOnNetworkStatusChange: true,
    pollInterval: pollDealTasks ? 2000 : 0,
    skip: currentView !== 'deals' || !selectedDealId,
    variables: { filters: { status: 'OPEN' } },
  });
  const [updateDealStatus, updateDealStatusState] = useMutation(
    UPDATE_DEAL_STATUS_MUTATION,
  );
  const [updateTask] = useMutation(UPDATE_TASK_MUTATION);

  const companies = companiesResult.data?.companies ?? [];
  const deals = dealsResult.data?.deals ?? [];
  const selectedCompany = companyDetailResult.data?.company ?? null;
  const selectedDeal = dealDetailResult.data?.deal ?? null;
  const companyActivities = (companyActivitiesResult.data?.activities ?? [])
    .slice()
    .sort((left, right) => sortNewestFirst(left.occurredAt, right.occurredAt));
  const companyTasks = (companyOpenTasksResult.data?.tasks ?? []).filter(
    (task) => task.companyId === selectedCompanyId,
  );
  const dealActivities = (dealActivitiesResult.data?.activities ?? [])
    .slice()
    .sort((left, right) => sortNewestFirst(left.occurredAt, right.occurredAt));
  const dealTasks = (dealOpenTasksResult.data?.tasks ?? []).filter(
    (task) => task.dealId === selectedDealId,
  );

  useEffect(() => {
    if (companies.length === 0) {
      setSelectedCompanyId(null);
      return;
    }

    const currentSelectionExists = companies.some(
      (company) => company.id === selectedCompanyId,
    );

    if (!currentSelectionExists) {
      setSelectedCompanyId(companies[0].id);
    }
  }, [companies, selectedCompanyId]);

  useEffect(() => {
    if (deals.length === 0) {
      setSelectedDealId(null);
      return;
    }

    const currentSelectionExists = deals.some((deal) => deal.id === selectedDealId);

    if (!currentSelectionExists) {
      setSelectedDealId(deals[0].id);
    }
  }, [deals, selectedDealId]);

  useEffect(() => {
    if (!pollDealTasks) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      setPollDealTasks(false);
    }, 12_000);

    return () => {
      window.clearTimeout(timer);
    };
  }, [pollDealTasks]);

  async function refreshCoreViews() {
    await Promise.all([companiesResult.refetch(), dealsResult.refetch()]);
  }

  async function refreshSelectedCompanyViews() {
    const work = [];

    if (currentView === 'companies' && selectedCompanyId) {
      work.push(
        companyDetailResult.refetch(),
        companyActivitiesResult.refetch(),
        companyOpenTasksResult.refetch(),
      );
    }

    if (work.length > 0) {
      await Promise.all(work);
    }
  }

  async function refreshSelectedDealViews() {
    const work = [];

    if (currentView === 'deals' && selectedDealId) {
      work.push(
        dealDetailResult.refetch(),
        dealActivitiesResult.refetch(),
        dealOpenTasksResult.refetch(),
      );
    }

    if (work.length > 0) {
      await Promise.all(work);
    }
  }

  async function refreshTaskList() {
    if (currentView === 'tasks') {
      await tasksResult.refetch();
    }
  }

  async function handleCompanySaved(company) {
    setCompanyDialog(null);
    await refreshCoreViews();
    setSelectedCompanyId(company.id);
    setCurrentView('companies');
  }

  async function handleContactSaved() {
    setContactDialog(null);
    await refreshSelectedCompanyViews();
  }

  async function handleDealSaved(deal) {
    setDealDialog(false);
    setSelectedDealId(deal.id);
    setCurrentView('deals');
    await refreshCoreViews();
    await refreshSelectedDealViews();
  }

  async function handleTaskSaved() {
    setTaskDialog(null);
    await Promise.all([
      refreshSelectedCompanyViews(),
      refreshSelectedDealViews(),
      refreshTaskList(),
    ]);
  }

  async function handleActivitySaved() {
    setActivityDialog(null);
    await Promise.all([refreshSelectedCompanyViews(), refreshSelectedDealViews()]);
  }

  async function handleTaskCompleted(taskId) {
    await updateTask({
      variables: {
        input: {
          status: 'COMPLETED',
          taskId,
        },
      },
    });

    await Promise.all([
      refreshSelectedCompanyViews(),
      refreshSelectedDealViews(),
      refreshTaskList(),
    ]);
  }

  async function handleDealStatusUpdated(nextStatus) {
    if (!selectedDealId) {
      return;
    }

    setDealStatusError(null);

    try {
      await updateDealStatus({
        variables: {
          input: {
            dealId: selectedDealId,
            status: nextStatus,
          },
        },
      });

      setDealStatusNotice(
        'Deal status updated. Follow-up tasks may appear shortly while downstream processing completes.',
      );
      setPollDealTasks(true);
      await Promise.all([
        refreshCoreViews(),
        refreshSelectedDealViews(),
        refreshTaskList(),
      ]);
    } catch (error) {
      setDealStatusError(error);
    }
  }

  const shellSections = [
    { key: 'companies', label: 'Companies' },
    { key: 'deals', label: 'Deals' },
    { key: 'tasks', label: 'Tasks' },
  ];

  return (
    <main className="app-shell">
      <aside className="app-sidebar">
        <div>
          <p className="eyebrow">PulseCRM</p>
          <h1>Internal workspace</h1>
          <p className="sidebar-copy">
            Gateway-backed CRM screens for companies, deals, tasks, and activity.
          </p>
        </div>

        <nav className="nav-list" aria-label="Primary navigation">
          {shellSections.map((section) => (
            <button
              key={section.key}
              className={
                currentView === section.key ? 'nav-button is-selected' : 'nav-button'
              }
              onClick={() => setCurrentView(section.key)}
              type="button"
            >
              {section.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-card">
            <p>{viewer.name}</p>
            <span className="pill">{formatEnumLabel(viewer.role)}</span>
            <small>{viewer.email}</small>
          </div>
          <button
            className="secondary-button signout-button"
            onClick={() => onLoggedOut()}
            type="button"
          >
            Sign out
          </button>
        </div>
      </aside>

      <section className="app-content">
        {currentView === 'companies' ? (
          <CompanyWorkspace
            companies={companies}
            companyActivities={companyActivities}
            companyDetail={
              selectedCompany
                ? {
                    ...selectedCompany,
                    deals: deals.filter((deal) => deal.companyId === selectedCompany.id),
                  }
                : null
            }
            companyError={companiesResult.error ?? companyDetailResult.error}
            companyLoading={
              companiesResult.loading ||
              (Boolean(selectedCompanyId) && companyDetailResult.loading)
            }
            companySearch={companySearch}
            onActivityRequested={() =>
              setActivityDialog({
                companyId: selectedCompanyId,
              })
            }
            onCompanySearchChange={setCompanySearch}
            onCompanySelected={setSelectedCompanyId}
            onContactCreated={() => setContactDialog({ contact: null })}
            onContactEdited={(contact) => setContactDialog({ contact })}
            onCreateCompany={() => setCompanyDialog({ company: null })}
            onCreateDeal={() => setDealDialog(true)}
            onCreateTask={() =>
              setTaskDialog({
                initialTask: null,
                initialValues: {
                  companyId: selectedCompanyId,
                },
              })
            }
            onEditCompany={() => setCompanyDialog({ company: selectedCompany })}
            onRelationshipFilterChange={setRelationshipFilter}
            onRetry={() => {
              companiesResult.refetch();
              refreshSelectedCompanyViews();
            }}
            relationshipFilter={relationshipFilter}
            selectedCompanyId={selectedCompanyId}
            tasks={companyTasks}
            viewer={viewer}
          />
        ) : null}

        {currentView === 'deals' ? (
          <DealsWorkspace
            dealActivities={dealActivities}
            dealDetail={selectedDeal}
            dealDetailError={dealDetailResult.error ?? dealActivitiesResult.error}
            dealDetailLoading={
              dealsResult.loading ||
              (Boolean(selectedDealId) &&
                (dealDetailResult.loading || dealActivitiesResult.loading))
            }
            dealSearch={dealSearch}
            deals={deals}
            dealsError={dealsResult.error}
            dealsLoading={dealsResult.loading}
            onActivityRequested={() =>
              setActivityDialog(
                selectedDeal
                  ? {
                      companyId: selectedDeal.companyId,
                      dealId: selectedDeal.id,
                      contactId: selectedDeal.primaryContactId,
                    }
                  : null,
              )
            }
            onCreateDeal={() => setDealDialog(true)}
            onCreateTask={() =>
              setTaskDialog(
                selectedDeal
                  ? {
                      initialTask: null,
                      initialValues: {
                        companyId: selectedDeal.companyId,
                        contactId: selectedDeal.primaryContactId,
                        dealId: selectedDeal.id,
                      },
                    }
                  : {
                      initialTask: null,
                      initialValues: null,
                    },
              )
            }
            onDealSearchChange={setDealSearch}
            onDealSelected={setSelectedDealId}
            onRetryDealDetail={refreshSelectedDealViews}
            onRetryDeals={dealsResult.refetch}
            onStatusFilterChange={setDealStatusFilter}
            onStatusUpdated={handleDealStatusUpdated}
            selectedDealId={selectedDealId}
            statusFilter={dealStatusFilter}
            tasks={dealTasks}
            updateState={{
              error: dealStatusError,
              loading: updateDealStatusState.loading,
              statusNotice: dealStatusNotice,
            }}
          />
        ) : null}

        {currentView === 'tasks' ? (
          <TasksWorkspace
            onCreateTask={() => setTaskDialog({ initialTask: null, initialValues: null })}
            onEditTask={(task) => setTaskDialog({ initialTask: task, initialValues: null })}
            onRetry={tasksResult.refetch}
            onScopeChange={setTaskScope}
            onStatusChange={setTaskStatusFilter}
            onTaskCompleted={handleTaskCompleted}
            scope={taskScope}
            status={taskStatusFilter}
            tasks={tasksResult.data?.tasks ?? []}
            tasksError={tasksResult.error}
            tasksLoading={tasksResult.loading}
            viewer={viewer}
          />
        ) : null}
      </section>

      <CompanyFormDialog
        companies={companies}
        initialCompany={companyDialog?.company ?? null}
        onClose={() => setCompanyDialog(null)}
        onSaved={handleCompanySaved}
        open={Boolean(companyDialog)}
      />

      <ContactFormDialog
        company={selectedCompany}
        initialContact={contactDialog?.contact ?? null}
        onClose={() => setContactDialog(null)}
        onSaved={handleContactSaved}
        open={Boolean(contactDialog)}
      />

      <DealFormDialog
        companies={companies}
        initialCompanyId={selectedCompanyId}
        onClose={() => setDealDialog(false)}
        onSaved={handleDealSaved}
        open={dealDialog}
      />

      <TaskFormDialog
        companies={companies}
        deals={deals}
        initialTask={taskDialog?.initialTask ?? null}
        initialValues={taskDialog?.initialValues ?? null}
        onClose={() => setTaskDialog(null)}
        onSaved={handleTaskSaved}
        open={Boolean(taskDialog)}
        viewer={viewer}
      />

      <ActivityFormDialog
        companies={companies}
        deals={deals}
        initialValues={activityDialog}
        onClose={() => setActivityDialog(null)}
        onSaved={handleActivitySaved}
        open={Boolean(activityDialog)}
        viewer={viewer}
      />
    </main>
  );
}

function AuthenticatedApp({ onLoggedOut, sessionMessage }) {
  const { data, error, loading, refetch } = useQuery(ME_QUERY, {
    fetchPolicy: 'network-only',
  });
  const isInvalidSession = !loading && !error && data?.me === null;

  useEffect(() => {
    if (isUnauthenticatedError(error)) {
      onLoggedOut('Your session is no longer valid. Sign in again.');
    }
  }, [error, onLoggedOut]);

  useEffect(() => {
    if (isInvalidSession) {
      onLoggedOut('Sign in to continue.');
    }
  }, [isInvalidSession, onLoggedOut]);

  if (loading || isInvalidSession) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <LoadingState
            label={isInvalidSession ? 'Returning to sign in' : 'Restoring your session'}
          />
        </section>
      </main>
    );
  }

  if (error && !isUnauthenticatedError(error)) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          {sessionMessage ? <InlineMessage tone="info">{sessionMessage}</InlineMessage> : null}
          <ErrorState
            actionLabel="Retry session check"
            message={getApolloErrorMessage(error)}
            onAction={refetch}
          />
          <button className="secondary-button" onClick={() => onLoggedOut()} type="button">
            Return to sign in
          </button>
        </section>
      </main>
    );
  }

  return <CrmWorkspace onLoggedOut={onLoggedOut} viewer={data.me} />;
}

function Dialog({ children, onClose, subtitle, title }) {
  return (
    <div className="dialog-backdrop" role="presentation">
      <section aria-modal="true" className="dialog-card" role="dialog">
        <div className="panel-header">
          <div>
            <p className="panel-eyebrow">Form</p>
            <h2>{title}</h2>
            <p className="subtle-copy">{subtitle}</p>
          </div>
          <button className="text-button" onClick={onClose} type="button">
            Close
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <article className="metric-card">
      <p>{label}</p>
      <strong>{value}</strong>
    </article>
  );
}

function InlineMessage({ children, tone }) {
  return <div className={`inline-message tone-${tone}`}>{children}</div>;
}

function EmptyState({ body, title }) {
  return (
    <div className="state-card">
      <strong>{title}</strong>
      <p>{body}</p>
    </div>
  );
}

function ErrorState({ actionLabel, message, onAction }) {
  return (
    <div className="state-card tone-error">
      <strong>Something went wrong</strong>
      <p>{message}</p>
      {onAction ? (
        <button className="secondary-button" onClick={onAction} type="button">
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}

function LoadingState({ label }) {
  return (
    <div className="state-card tone-info">
      <strong>{label}</strong>
      <p>The UI is waiting on the GraphQL gateway.</p>
    </div>
  );
}

export function App() {
  const [token, setToken] = useState(() => getStoredAuthToken());
  const [sessionMessage, setSessionMessage] = useState('');

  function handleLoggedIn(nextToken) {
    setStoredAuthToken(nextToken);
    setSessionMessage('');
    setToken(nextToken);
  }

  function handleLoggedOut(message = '') {
    clearStoredAuthToken();
    setToken(null);
    setSessionMessage(typeof message === 'string' ? message : '');
  }

  return token ? (
    <AuthenticatedApp onLoggedOut={handleLoggedOut} sessionMessage={sessionMessage} />
  ) : (
    <LoginScreen key={AUTH_STORAGE_KEY} message={sessionMessage} onLoggedIn={handleLoggedIn} />
  );
}
