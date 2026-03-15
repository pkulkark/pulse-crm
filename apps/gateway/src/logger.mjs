export function logJson(logger, level, event, fields = {}) {
  const logMethod =
    typeof logger[level] === 'function'
      ? logger[level].bind(logger)
      : console.log;

  logMethod(
    JSON.stringify({
      event,
      ...fields,
    }),
  );
}

export function serializeError(error) {
  if (!(error instanceof Error)) {
    return { message: String(error) };
  }

  return {
    message: error.message,
    name: error.name,
  };
}
