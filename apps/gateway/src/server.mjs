import http from 'node:http';
import { URL } from 'node:url';

import { ApolloGateway, IntrospectAndCompose, RemoteGraphQLDataSource } from '@apollo/gateway';
import { ApolloServer, HeaderMap } from '@apollo/server';

import { AuthTokenError } from './auth.mjs';
import { getGatewayConfig } from './config.mjs';
import { CONTEXT_HEADERS, createRequestContext } from './context.mjs';
import { logJson, serializeError } from './logger.mjs';

function jsonResponse(response, statusCode, payload) {
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

  if (rawBody.length === 0) {
    return {};
  }

  return JSON.parse(rawBody);
}

function createHeaderMap(headers) {
  const headerMap = new HeaderMap();

  for (const [name, value] of Object.entries(headers)) {
    if (Array.isArray(value)) {
      for (const entry of value) {
        headerMap.append(name, entry);
      }
      continue;
    }

    if (typeof value === 'string') {
      headerMap.set(name, value);
    }
  }

  return headerMap;
}

class ContextPropagatingDataSource extends RemoteGraphQLDataSource {
  constructor({ logger, serviceName, url }) {
    super({ url });
    this.logger = logger;
    this.serviceName = serviceName;
  }

  willSendRequest({ context, request }) {
    const requestContext = context?.requestContext;

    if (!requestContext) {
      logJson(this.logger, 'info', 'subgraph_introspection_request', {
        subgraph: this.serviceName,
      });
      return;
    }

    const { request: requestDetails, user } = requestContext;

    request.http.headers.set(
      CONTEXT_HEADERS.correlationId,
      requestDetails.correlationId,
    );
    request.http.headers.set(CONTEXT_HEADERS.userRole, user.role);

    if (user.id) {
      request.http.headers.set(CONTEXT_HEADERS.userId, user.id);
    }

    if (user.companyId) {
      request.http.headers.set(CONTEXT_HEADERS.companyId, user.companyId);
    }

    logJson(this.logger, 'info', 'subgraph_request', {
      companyId: user.companyId,
      correlationId: requestDetails.correlationId,
      subgraph: this.serviceName,
      userId: user.id,
      userRole: user.role,
    });
  }

  didReceiveResponse({ context, response }) {
    const requestContext = context?.requestContext;

    if (!requestContext) {
      return response;
    }

    logJson(this.logger, 'info', 'subgraph_response', {
      correlationId: requestContext.request.correlationId,
      statusCode: response.http.status,
      subgraph: this.serviceName,
    });

    return response;
  }
}

async function sendGraphQLResponse(response, graphQLResponse) {
  const headers = {};

  graphQLResponse.headers.forEach((value, key) => {
    headers[key] = value;
  });

  response.writeHead(graphQLResponse.status ?? 200, headers);

  if (graphQLResponse.body.kind === 'complete') {
    response.end(graphQLResponse.body.string);
    return;
  }

  for await (const chunk of graphQLResponse.body.asyncIterator) {
    response.write(chunk);
  }

  response.end();
}

function createLoggingPlugin(logger) {
  return {
    async requestDidStart(requestContext) {
      const startedAt = Date.now();
      const correlationId =
        requestContext.contextValue.requestContext.request.correlationId;

      logJson(logger, 'info', 'gateway_graphql_request', {
        correlationId,
        operationName: requestContext.request.operationName ?? null,
      });

      return {
        async didEncounterErrors(context) {
          for (const error of context.errors) {
            logJson(logger, 'error', 'gateway_graphql_error', {
              correlationId,
              error: serializeError(error.originalError ?? error),
            });
          }
        },
        async willSendResponse(context) {
          logJson(logger, 'info', 'gateway_graphql_response', {
            correlationId,
            durationMs: Date.now() - startedAt,
            errorCount: context.errors?.length ?? 0,
          });
        },
      };
    },
  };
}

async function createApolloServer({ gatewayConfig, logger }) {
  const gateway = new ApolloGateway({
    buildService({ name, url }) {
      return new ContextPropagatingDataSource({
        logger,
        serviceName: name,
        url,
      });
    },
    supergraphSdl: new IntrospectAndCompose({
      subgraphs: gatewayConfig.enabledSubgraphs,
    }),
  });

  const server = new ApolloServer({
    gateway,
    introspection: true,
    plugins: [createLoggingPlugin(logger)],
  });

  await server.start();

  return { gateway, server };
}

function createRequestRouter({ apolloServer, gatewayConfig, logger }) {
  return async function handleRequest(request, response) {
    const requestUrl = new URL(request.url ?? '/', 'http://localhost');

    if (
      requestUrl.pathname === '/health' ||
      requestUrl.pathname === '/health/'
    ) {
      return jsonResponse(response, 200, {
        graphql: '/',
        ready: true,
        service: gatewayConfig.gatewayName,
        status: 'ok',
        subgraphs: gatewayConfig.enabledSubgraphs.map(({ name }) => name),
      });
    }

    if (requestUrl.pathname !== '/') {
      return jsonResponse(response, 404, {
        error: 'Not found',
      });
    }

    if (request.method !== 'POST') {
      response.writeHead(405, {
        Allow: 'POST',
        'Content-Type': 'application/json; charset=utf-8',
      });
      response.end(
        JSON.stringify({
          error: 'GraphQL requests must use POST.',
        }),
      );
      return;
    }

    try {
      const contextValue = {
        requestContext: createRequestContext(request, {
          secret: gatewayConfig.authTokenSecret,
        }),
      };
      const body = await readJsonBody(request);
      const graphQLResponse = await apolloServer.executeHTTPGraphQLRequest({
        context: async () => contextValue,
        httpGraphQLRequest: {
          body,
          headers: createHeaderMap(request.headers),
          method: request.method,
          search: requestUrl.search,
        },
      });

      await sendGraphQLResponse(response, graphQLResponse);
    } catch (error) {
      if (error instanceof SyntaxError) {
        jsonResponse(response, 400, {
          errors: [
            {
              message: 'GraphQL request body must be valid JSON.',
            },
          ],
        });
        return;
      }

      if (error instanceof AuthTokenError) {
        jsonResponse(response, 401, {
          errors: [
            {
              message: error.message,
            },
          ],
        });
        return;
      }

      logJson(logger, 'error', 'gateway_http_error', {
        correlationId:
          normalizeHeaderCorrelationId(request.headers) ?? 'unknown',
        error: serializeError(error),
      });

      jsonResponse(response, 500, {
        errors: [
          {
            message: 'Gateway request handling failed.',
          },
        ],
      });
    }
  };
}

function normalizeHeaderCorrelationId(headers) {
  const correlationId = headers[CONTEXT_HEADERS.correlationId];

  if (Array.isArray(correlationId)) {
    return correlationId[0] ?? null;
  }

  return typeof correlationId === 'string' && correlationId.trim().length > 0
    ? correlationId.trim()
    : null;
}

export async function createServer(options = {}) {
  const logger = options.logger ?? console;
  const gatewayConfig = options.gatewayConfig ?? getGatewayConfig(options.env);
  const { gateway, server: apolloServer } = await createApolloServer({
    gatewayConfig,
    logger,
  });
  const requestRouter = createRequestRouter({
    apolloServer,
    gatewayConfig,
    logger,
  });
  const httpServer = http.createServer((request, response) => {
    void requestRouter(request, response);
  });

  async function stop() {
    await apolloServer.stop();
    if (typeof gateway.stop === 'function') {
      await gateway.stop();
    }

    await new Promise((resolve, reject) => {
      httpServer.close((error) => {
        if (error) {
          reject(error);
          return;
        }

        resolve();
      });
    });
  }

  return {
    gatewayConfig,
    server: httpServer,
    stop,
  };
}

export async function startGatewayServer(options = {}) {
  const logger = options.logger ?? console;
  const gatewayConfig = options.gatewayConfig ?? getGatewayConfig(options.env);
  const { server, stop } = await createServer({ gatewayConfig, logger });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(gatewayConfig.port, gatewayConfig.host, resolve);
  });

  const address = server.address();
  const url =
    typeof address === 'object' && address
      ? `http://${gatewayConfig.host}:${address.port}`
      : null;

  logJson(logger, 'info', 'gateway_started', {
    port: typeof address === 'object' && address ? address.port : null,
    subgraphs: gatewayConfig.enabledSubgraphs.map(({ name }) => name),
  });

  return {
    gatewayConfig,
    server,
    stop,
    url,
  };
}

if (process.env.NODE_ENV !== 'test') {
  startGatewayServer().catch((error) => {
    logJson(console, 'error', 'gateway_startup_failed', {
      error: serializeError(error),
    });
    process.exitCode = 1;
  });
}
