import crypto from 'node:crypto';

import { authenticateRequest } from './auth.mjs';

export const CONTEXT_HEADERS = Object.freeze({
  companyId: 'x-company-id',
  correlationId: 'x-correlation-id',
  userId: 'x-user-id',
  userRole: 'x-user-role',
});

function normalizeHeaderValue(value) {
  if (Array.isArray(value)) {
    return value[0] ?? null;
  }

  if (typeof value !== 'string') {
    return null;
  }

  const trimmedValue = value.trim();
  return trimmedValue.length > 0 ? trimmedValue : null;
}

export function createRequestContext(request, authOptions) {
  const correlationId =
    normalizeHeaderValue(request.headers[CONTEXT_HEADERS.correlationId]) ??
    crypto.randomUUID();
  const user = authenticateRequest(request.headers, authOptions);

  return {
    request: {
      clientIp: request.socket?.remoteAddress ?? null,
      correlationId,
    },
    user,
  };
}
