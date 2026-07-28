import { NextFunction, Request, Response } from "express";
import logger from "../config/logger.js";
import { env } from "../config/index.js";
import type { HttpError } from "../types/index.js";

export function errorHandler(err: HttpError, req: Request, res: Response, next: NextFunction) {
  const status = err.status ?? err.statusCode ?? 500;
  const message = err.message || "Internal server error";

  logger.error(`${req.method} ${req.originalUrl} ${status} - ${message}`);

  const payload: Record<string, unknown> = {
    status,
    error: status === 500 ? "Internal server error" : message,
  };

  if (env.nodeEnv !== "production" && err.stack) {
    payload.stack = err.stack;
  }

  res.status(status).json(payload);
}
