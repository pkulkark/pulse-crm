import assert from 'node:assert/strict';
import http from 'node:http';
import test from 'node:test';

process.env.NODE_ENV = 'test';

const { startGatewayServer } = await import('./server.mjs');

const SUBGRAPH_SDL = `
  type RequestContext {
    correlationId: ID!
    userId: String
    userRole: String!
  }

  type ServiceHealth {
    service: String!
    status: String!
    requestContext: RequestContext!
  }

  type Query {
    serviceHealth: ServiceHealth!
  }
`;

function createLogger() {
  const entries = [];

  return {
    entries,
    error(message) {
      entries.push({ level: 'error', message });
    },
    info(message) {
      entries.push({ level: 'info', message });
    },
  };
}

function writeJson(response, statusCode, payload) {
  response.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
  });
  response.end(JSON.stringify(payload));
}

async function readJsonBody(request) {
  let rawBody = '';

  for await (const chunk of request) {
    rawBody += chunk;
  }

  return rawBody.length === 0 ? {} : JSON.parse(rawBody);
}

async function createMockSubgraphServer({ failQueries = false } = {}) {
  const requests = [];
  const server = http.createServer(async (request, response) => {
    const body = await readJsonBody(request);

    requests.push({
      body,
      headers: request.headers,
    });

    if ((body.query ?? '').includes('_service')) {
      writeJson(response, 200, {
        data: {
          _service: {
            sdl: SUBGRAPH_SDL,
          },
        },
      });
      return;
    }

    if (failQueries) {
      writeJson(response, 503, {
        errors: [
          {
            message: 'Subgraph unavailable.',
          },
        ],
      });
      return;
    }

    if ((body.query ?? '').includes('serviceHealth')) {
      writeJson(response, 200, {
        data: {
          serviceHealth: {
            requestContext: {
              correlationId: request.headers['x-correlation-id'],
              userId: request.headers['x-user-id'] ?? null,
              userRole: request.headers['x-user-role'] ?? 'anonymous',
            },
            service: 'crm-relationships-service',
            status: 'ok',
          },
        },
      });
      return;
    }

    writeJson(response, 400, {
      errors: [
        {
          message: 'Unsupported mock subgraph query.',
        },
      ],
    });
  });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });

  const address = server.address();

  return {
    requests,
    stop: async () => {
      await new Promise((resolve, reject) => {
        server.close((error) => {
          if (error) {
            reject(error);
            return;
          }

          resolve();
        });
      });
    },
    url: `http://127.0.0.1:${address.port}/graphql/`,
  };
}

async function startTestGateway({ failQueries = false } = {}) {
  const downstream = await createMockSubgraphServer({ failQueries });
  const logger = createLogger();
  const gateway = await startGatewayServer({
    gatewayConfig: {
      enabledSubgraphs: [
        {
          name: 'crmRelationships',
          url: downstream.url,
        },
      ],
      gatewayName: 'test-gateway',
      host: '127.0.0.1',
      port: 0,
      subgraphs: [
        {
          enabled: true,
          name: 'crmRelationships',
          url: downstream.url,
        },
      ],
    },
    logger,
  });

  return {
    downstream,
    gateway,
    logger,
    stop: async () => {
      await gateway.stop();
      await downstream.stop();
    },
  };
}

test('ready endpoint responds with gateway status and enabled subgraphs', async (t) => {
  const runtime = await startTestGateway();
  t.after(async () => runtime.stop());

  const response = await fetch(`${runtime.gateway.url}/ready`);

  assert.equal(response.status, 200);

  const payload = await response.json();
  assert.equal(payload.status, 'ok');
  assert.equal(payload.ready, true);
  assert.deepEqual(payload.subgraphs, ['crmRelationships']);
});

test('gateway resolves serviceHealth through the downstream subgraph', async (t) => {
  const runtime = await startTestGateway();
  t.after(async () => runtime.stop());

  const response = await fetch(`${runtime.gateway.url}/graphql`, {
    body: JSON.stringify({
      operationName: 'ServiceHealthCheck',
      query: `
        query ServiceHealthCheck {
          serviceHealth {
            service
            status
            requestContext {
              correlationId
              userId
              userRole
            }
          }
        }
      `,
    }),
    headers: {
      'content-type': 'application/json',
      'x-correlation-id': 'corr-123',
      'x-user-id': 'user-42',
      'x-user-role': 'manager',
    },
    method: 'POST',
  });

  assert.equal(response.status, 200);

  const payload = await response.json();
  assert.deepEqual(payload.data.serviceHealth, {
    requestContext: {
      correlationId: 'corr-123',
      userId: 'user-42',
      userRole: 'manager',
    },
    service: 'crm-relationships-service',
    status: 'ok',
  });

  const runtimeRequest = runtime.downstream.requests.find(
    ({ body }) =>
      typeof body.query === 'string' &&
      body.query.includes('serviceHealth') &&
      !body.query.includes('_service'),
  );

  assert.equal(runtimeRequest.headers['x-correlation-id'], 'corr-123');
  assert.equal(runtimeRequest.headers['x-user-id'], 'user-42');
  assert.equal(runtimeRequest.headers['x-user-role'], 'manager');
});

test('gateway returns a clear GraphQL error when the downstream query fails', async (t) => {
  const runtime = await startTestGateway({ failQueries: true });
  t.after(async () => runtime.stop());

  const response = await fetch(`${runtime.gateway.url}/graphql`, {
    body: JSON.stringify({
      query: `
        query BrokenServiceHealth {
          serviceHealth {
            status
          }
        }
      `,
    }),
    headers: {
      'content-type': 'application/json',
    },
    method: 'POST',
  });

  assert.equal(response.status, 200);

  const payload = await response.json();
  assert.equal(payload.data, null);
  assert.match(
    payload.errors[0].message,
    /503: Service Unavailable|crmRelationships|Subgraph unavailable/i,
  );
});
