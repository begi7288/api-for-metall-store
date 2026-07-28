import "../config/env.js";
import { PrismaClient } from "@prisma/client";
import logger from "../config/logger.js";

const databaseUrl = process.env.DATABASE_URL?.trim();
if (!databaseUrl) {
  throw new Error("DATABASE_URL environment variable is required for database connectivity.");
}

declare global {
  // eslint-disable-next-line no-var
  var __prisma: PrismaClient | undefined;
}

const prisma = global.__prisma ?? new PrismaClient({
  datasources: {
    db: {
      url: databaseUrl,
    },
  },
});

if (process.env.NODE_ENV !== "production") {
  global.__prisma = prisma;
}

async function connectDatabase() {
  try {
    await prisma.$connect();
    logger.info("Database connection established");
  } catch (error) {
    logger.error("Database connection failed:", error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}

connectDatabase();

export default prisma;
