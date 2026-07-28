import fs from "fs";
import dotenv from "dotenv";

// Load .env if present. This is safe to call in production since dotenv
// won't overwrite already-set environment variables.
dotenv.config({ path: process.env.DOTENV_PATH ?? ".env" });

const MIN_SECRET_LENGTH = 32;

function readFromFileFallback(name: string): string | undefined {
  const filePath = process.env[`${name}_FILE`];
  if (!filePath) return undefined;

  try {
    const content = fs.readFileSync(filePath, "utf8").trim();
    return content || undefined;
  } catch (err) {
    // If the file can't be read, surface a helpful error later where used.
    return undefined;
  }
}

function requiredEnv(name: string): string {
  const fromEnv = process.env[name];
  if (fromEnv && fromEnv.trim() !== "") return fromEnv.trim();

  const fromFile = readFromFileFallback(name);
  if (fromFile) return fromFile;

  throw new Error(`Environment variable ${name} is required but was not found.`);
}

function requiredSecret(name: string): string {
  const value = requiredEnv(name).trim();

  if (value.length < MIN_SECRET_LENGTH) {
    throw new Error(
      `Environment variable ${name} must be at least ${MIN_SECRET_LENGTH} characters long for secure JWT signing.`,
    );
  }

  return value;
}

function parsePositiveNumber(name: string, rawValue: string | undefined, fallback: number): number {
  if (rawValue === undefined) {
    return fallback;
  }

  const value = Number(rawValue);
  if (!Number.isFinite(value) || value <= 0 || Number.isNaN(value)) {
    throw new Error(`Environment variable ${name} must be a positive integer. Received: ${rawValue}`);
  }

  return value;
}

function parseBoolean(name: string, rawValue: string | undefined, fallback: boolean): boolean {
  if (rawValue === undefined) {
    return fallback;
  }

  const normalized = rawValue.trim().toLowerCase();
  if (normalized === "true") return true;
  if (normalized === "false") return false;

  throw new Error(`Environment variable ${name} must be "true" or "false". Received: ${rawValue}`);
}

function parsePort(rawValue: string | undefined, fallback: number): number {
  if (rawValue === undefined) {
    return fallback;
  }

  const port = Number(rawValue);
  if (!Number.isFinite(port) || port <= 0 || port > 65535 || Number.isNaN(port) || !Number.isInteger(port)) {
    throw new Error(`Environment variable PORT must be a valid positive integer between 1 and 65535. Received: ${rawValue}`);
  }

  return port;
}

function loadFrontendUrl(): string {
  const frontendUrl = process.env.FRONTEND_URL?.trim() ?? readFromFileFallback("FRONTEND_URL");

  if (frontendUrl) {
    return frontendUrl;
  }

  if ((process.env.NODE_ENV ?? "development").trim() === "development") {
    return "http://localhost:3000";
  }

  throw new Error("Environment variable FRONTEND_URL is required in production.");
}

export const env = {
  nodeEnv: (process.env.NODE_ENV ?? "development").trim(),
  port: parsePort(process.env.PORT, 3000),
  databaseUrl: requiredEnv("DATABASE_URL"),
  jwtSecret: requiredSecret("JWT_SECRET"),
  jwtExpiresIn: process.env.JWT_EXPIRES_IN ?? "1h",
  frontendUrl: loadFrontendUrl(),
  corsAllowCredentials: parseBoolean("CORS_ALLOW_CREDENTIALS", process.env.CORS_ALLOW_CREDENTIALS, false),
  logLevel: process.env.LOG_LEVEL ?? "info",
  rateLimitWindowMs: parsePositiveNumber("RATE_LIMIT_WINDOW_MS", process.env.RATE_LIMIT_WINDOW_MS, 15 * 60 * 1000),
  rateLimitMax: parsePositiveNumber("RATE_LIMIT_MAX", process.env.RATE_LIMIT_MAX, 100),
};
