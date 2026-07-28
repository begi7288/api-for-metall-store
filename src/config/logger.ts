import winston from "winston";
import { env } from "./index.js";

const { combine, colorize, timestamp, printf, errors } = winston.format;

const logFormat = combine(
  timestamp({ format: "YYYY-MM-DD HH:mm:ss" }),
  errors({ stack: true }),
  colorize({ all: true }),
  printf(({ timestamp, level, message, stack }) => {
    return stack
      ? `${timestamp} ${level}: ${message} - ${stack}`
      : `${timestamp} ${level}: ${message}`;
  }),
);

const logger = winston.createLogger({
  level: env.logLevel,
  format: logFormat,
  transports: [new winston.transports.Console()],
});

export default logger;
