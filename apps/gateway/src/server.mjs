import http from 'node:http';

const port = Number.parseInt(process.env.PORT ?? '4000', 10);
const gatewayName = process.env.GATEWAY_NAME ?? 'samplecrm-gateway';

function jsonResponse(response, statusCode, payload) {
  response.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
  });
  response.end(JSON.stringify(payload));
}

export function handleRequest(request, response) {
  if (request.url === '/health') {
    return jsonResponse(response, 200, {
      service: gatewayName,
      status: 'ok',
      phase: 'phase-0',
    });
  }

  if (request.url === '/') {
    return jsonResponse(response, 200, {
      message:
        'Gateway placeholder for Phase 0. GraphQL wiring starts in Phase 1.',
      health: '/health',
    });
  }

  return jsonResponse(response, 404, {
    error: 'Not found',
  });
}

export function createServer() {
  return http.createServer(handleRequest);
}

if (process.env.NODE_ENV !== 'test') {
  const server = createServer();
  server.listen(port, '0.0.0.0', () => {
    console.log(`Gateway placeholder listening on ${port}`);
  });
}
