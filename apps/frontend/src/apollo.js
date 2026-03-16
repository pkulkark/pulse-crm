import { ApolloClient, ApolloLink, HttpLink, InMemoryCache, from } from '@apollo/client';

export const AUTH_STORAGE_KEY = 'samplecrm.authToken';

export function getStoredAuthToken() {
  return window.localStorage.getItem(AUTH_STORAGE_KEY);
}

export function setStoredAuthToken(token) {
  window.localStorage.setItem(AUTH_STORAGE_KEY, token);
}

export function clearStoredAuthToken() {
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}

export function withAuthHeaders(headers = {}, token = getStoredAuthToken()) {
  if (!token) {
    return headers;
  }

  return {
    ...headers,
    authorization: `Bearer ${token}`,
  };
}

function normalizeGatewayUrl() {
  const configuredUrl = import.meta.env.VITE_GATEWAY_URL ?? 'http://localhost:4000';
  const parsedUrl = new URL(configuredUrl);

  if (
    window.location.hostname &&
    ['localhost', '127.0.0.1'].includes(parsedUrl.hostname)
  ) {
    parsedUrl.hostname = window.location.hostname;
  }

  return parsedUrl.toString();
}

export const gatewayUrl = normalizeGatewayUrl();

const authLink = new ApolloLink((operation, forward) => {
  operation.setContext(({ headers = {} }) => ({
    headers: withAuthHeaders(headers),
  }));

  return forward(operation);
});

const httpLink = new HttpLink({
  uri: gatewayUrl,
});

export const apolloClient = new ApolloClient({
  cache: new InMemoryCache(),
  link: from([authLink, httpLink]),
});
