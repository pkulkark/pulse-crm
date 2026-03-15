function parseBooleanFlag(value, defaultValue) {
  if (value == null) {
    return defaultValue;
  }

  return value.toLowerCase() === 'true';
}

export function getGatewayConfig(env = process.env) {
  const port = Number.parseInt(env.PORT ?? '4000', 10);

  if (Number.isNaN(port)) {
    throw new Error(`Invalid gateway port: ${env.PORT}`);
  }

  const subgraphs = [
    {
      enabled: parseBooleanFlag(
        env.CRM_RELATIONSHIPS_GRAPHQL_ENABLED,
        true,
      ),
      name: 'crmRelationships',
      url:
        env.CRM_RELATIONSHIPS_GRAPHQL_URL ??
        'http://127.0.0.1:8002/graphql/',
    },
    {
      enabled: parseBooleanFlag(env.IDENTITY_GRAPHQL_ENABLED, false),
      name: 'identity',
      url: env.IDENTITY_GRAPHQL_URL ?? 'http://127.0.0.1:8001/graphql/',
    },
    {
      enabled: parseBooleanFlag(env.DEALS_GRAPHQL_ENABLED, false),
      name: 'deals',
      url: env.DEALS_GRAPHQL_URL ?? 'http://127.0.0.1:8003/graphql/',
    },
  ];

  const enabledSubgraphs = subgraphs
    .filter(({ enabled }) => enabled)
    .map((serviceDefinition) => ({
      name: serviceDefinition.name,
      url: serviceDefinition.url,
    }));

  if (enabledSubgraphs.length === 0) {
    throw new Error('At least one GraphQL subgraph must be enabled.');
  }

  return {
    enabledSubgraphs,
    gatewayName: env.GATEWAY_NAME ?? 'samplecrm-gateway',
    host: env.HOST ?? '0.0.0.0',
    port,
    subgraphs,
  };
}
