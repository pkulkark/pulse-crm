import crypto from 'node:crypto';

function base64urlEncode(value) {
  return Buffer.from(value)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
}

function base64urlDecode(value) {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  const paddingLength = (4 - (normalized.length % 4)) % 4;
  const padded = normalized + '='.repeat(paddingLength);

  return Buffer.from(padded, 'base64').toString('utf8');
}

function createSignature(signingInput, secret) {
  return crypto.createHmac('sha256', secret).update(signingInput).digest();
}

export class AuthTokenError extends Error {
  constructor(message = 'Invalid or expired authentication token.') {
    super(message);
    this.name = 'AuthTokenError';
  }
}

export function createAccessToken(
  { companyId, role, userId },
  { expiresInSeconds = 60 * 60, now = Date.now(), secret },
) {
  const issuedAt = Math.floor(now / 1000);
  const header = { alg: 'HS256', typ: 'JWT' };
  const payload = {
    companyId,
    exp: issuedAt + expiresInSeconds,
    iat: issuedAt,
    role,
    sub: userId,
  };
  const encodedHeader = base64urlEncode(JSON.stringify(header));
  const encodedPayload = base64urlEncode(JSON.stringify(payload));
  const signingInput = `${encodedHeader}.${encodedPayload}`;
  const signature = base64urlEncode(createSignature(signingInput, secret));

  return `${signingInput}.${signature}`;
}

function parseBearerToken(headerValue) {
  if (typeof headerValue !== 'string') {
    return null;
  }

  const [scheme, token] = headerValue.trim().split(/\s+/, 2);
  if (scheme?.toLowerCase() !== 'bearer' || !token) {
    throw new AuthTokenError();
  }

  return token;
}

export function authenticateRequest(headers, { now = Date.now(), secret }) {
  const token = parseBearerToken(headers.authorization);

  if (!token) {
    return {
      companyId: null,
      id: null,
      role: 'anonymous',
    };
  }

  const segments = token.split('.');

  if (segments.length !== 3) {
    throw new AuthTokenError();
  }

  const [encodedHeader, encodedPayload, encodedSignature] = segments;
  const signingInput = `${encodedHeader}.${encodedPayload}`;
  const expectedSignature = base64urlEncode(createSignature(signingInput, secret));
  const receivedSignatureBuffer = Buffer.from(encodedSignature);
  const expectedSignatureBuffer = Buffer.from(expectedSignature);

  if (
    receivedSignatureBuffer.length !== expectedSignatureBuffer.length ||
    !crypto.timingSafeEqual(
      receivedSignatureBuffer,
      expectedSignatureBuffer,
    )
  ) {
    throw new AuthTokenError();
  }

  let payload;
  try {
    payload = JSON.parse(base64urlDecode(encodedPayload));
  } catch {
    throw new AuthTokenError();
  }

  if (
    typeof payload.sub !== 'string' ||
    typeof payload.role !== 'string' ||
    typeof payload.companyId !== 'string' ||
    typeof payload.exp !== 'number' ||
    payload.exp <= Math.floor(now / 1000)
  ) {
    throw new AuthTokenError();
  }

  return {
    companyId: payload.companyId,
    id: payload.sub,
    role: payload.role,
  };
}
