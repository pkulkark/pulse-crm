import assert from 'node:assert/strict';
import test from 'node:test';

process.env.NODE_ENV = 'test';

const { handleRequest } = await import('./server.mjs');

function createMockResponse() {
  return {
    body: '',
    headers: {},
    statusCode: null,
    writeHead(statusCode, headers) {
      this.statusCode = statusCode;
      this.headers = headers;
    },
    end(body) {
      this.body = body;
    },
  };
}

test('health endpoint responds with service status', () => {
  const response = createMockResponse();

  handleRequest({ url: '/health' }, response);

  assert.equal(response.statusCode, 200);
  const payload = JSON.parse(response.body);
  assert.equal(payload.status, 'ok');
  assert.equal(payload.phase, 'phase-0');
});

test('root endpoint exposes placeholder payload', () => {
  const response = createMockResponse();

  handleRequest({ url: '/' }, response);

  assert.equal(response.statusCode, 200);
  const payload = JSON.parse(response.body);
  assert.match(payload.message, /Phase 0/);
});
