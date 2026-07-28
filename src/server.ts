import app from "./app.js";
import logger from "./config/logger.js";
import prisma from "./prisma/client.js";

function parsePort(rawValue: string | undefined, fallback: number): number {
  if (!rawValue?.trim()) {
    return fallback;
  }

  const port = Number(rawValue);
  if (!Number.isFinite(port) || !Number.isInteger(port) || port <= 0 || port > 65535) {
    throw new Error(`Invalid PORT value: ${rawValue}`);
  }

  return port;
}

const port = parsePort(process.env.PORT, 3000);

const server = app.listen(port, () => {
  logger.info(`Server listening on port ${port}`);
});

server.on("error", (error: NodeJS.ErrnoException) => {
  logger.error("Server error:", error);
  if (error.code === "EADDRINUSE") {
    logger.error(`Port ${port} is already in use.`);
  }
  process.exit(1);
});

const shutdown = async (signal: string) => {
  logger.info(`Received ${signal}. Shutting down gracefully.`);
  server.close(async () => {
    await prisma.$disconnect();
    process.exit(0);
  });
};

process.on("unhandledRejection", (reason) => {
  logger.error("Unhandled promise rejection:", reason instanceof Error ? reason : String(reason));
  shutdown("unhandledRejection");
});

process.on("uncaughtException", (error) => {
  logger.error("Uncaught exception:", error);
  shutdown("uncaughtException");
});

process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
