import { FastifyLoggerInstance } from 'fastify';

let logger: FastifyLoggerInstance;

export function initLogger(fastifyLogger: FastifyLoggerInstance) {
  logger = fastifyLogger;
}

type ErrorWithStack = {
  message: string;
  stackTrace?: string;
  details?: unknown;
};

function formatError(error: unknown): ErrorWithStack {
  const err = error instanceof Error ? error : new Error(String(error));

  // Handle Supabase errors which might be objects
  const details = typeof error === 'object' && error !== null ? error : { originalError: error };

  return {
    message: err.message || err.toString(),
    stackTrace: err.stack,
    details,
  };
}

export function logError(message: string, error: unknown) {
  if (!logger) {
    throw new Error('Logger not initialized');
  }
  const formattedError = formatError(error);
  logger.error({
    message,
    error: formattedError.message,
    stackTrace: formattedError.stackTrace,
    details: formattedError.details,
  });
}

export function logInfo(message: string, data?: unknown) {
  if (!logger) {
    throw new Error('Logger not initialized');
  }
  logger.info({ message, data });
}
