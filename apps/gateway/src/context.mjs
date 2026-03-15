import crypto from 'node:crypto';

export const CONTEXT_HEADERS = Object.freeze({
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

export function createRequestContext(request) {
  const correlationId =
    normalizeHeaderValue(request.headers[CONTEXT_HEADERS.correlationId]) ??
    crypto.randomUUID();
  const userId = normalizeHeaderValue(request.headers[CONTEXT_HEADERS.userId]);
  const userRole =
    normalizeHeaderValue(request.headers[CONTEXT_HEADERS.userRole]) ??
    'anonymous';

  return {
    request: {
      clientIp: request.socket?.remoteAddress ?? null,
      correlationId,
    },
    user: {
      id: userId,
      role: userRole,
    },
  };
}
