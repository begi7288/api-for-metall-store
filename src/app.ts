import express from "express";
import cors from "cors";
import helmet from "helmet";
import path from "path";
import { env } from "./config/index.js";
import swaggerUi from "swagger-ui-express";
import swaggerDocument from "./docs/swagger.js";
import routes from "./routes/index.js";
import prisma from "./prisma/client.js";
import { errorHandler } from "./middleware/error.middleware.js";
import { requestLogger } from "./middleware/logging.middleware.js";
import { apiRateLimiter } from "./middleware/rate-limit.middleware.js";

const app = express();
app.set("trust proxy", 1);

const allowedOrigin = env.frontendUrl;

app.use(helmet());
app.use(
  cors({
    origin: (incomingOrigin, callback) => {
      // Allow non-browser requests like curl/postman
      if (!incomingOrigin) return callback(null, true);

      // Allow the configured frontend origin
      if (incomingOrigin === allowedOrigin) return callback(null, true);

      // In development allow localhost origins (ports vary)
      if ((env.nodeEnv ?? "development") === "development") {
        try {
          const url = new URL(incomingOrigin);
          if (url.hostname === "localhost" || url.hostname === "127.0.0.1") {
            return callback(null, true);
          }
        } catch (err) {
          // Fall through to deny
        }
      }

      // Otherwise deny
      return callback(new Error("CORS policy: This origin is not allowed."), false);
    },
    credentials: env.corsAllowCredentials,
  }),
);
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(requestLogger);
app.use(apiRateLimiter);
app.use("/uploads", express.static(path.join(process.cwd(), "uploads")));
app.use("/docs", swaggerUi.serve, swaggerUi.setup(swaggerDocument));

app.get("/", (_req, res) => {
  res.status(200).json({
    message: "Metal Store API is running",
    docs: "/docs",
    endpoints: ["/auth/register", "/auth/login", "/user/me"],
  });
});

app.use(routes);

app.get("/healthz", async (_req, res) => {
  try {
    await prisma.$queryRaw`SELECT 1`;
    res.status(200).json({ status: "ok" });
  } catch (error) {
    res.status(503).json({ status: "error", message: "Database unreachable" });
  }
});

app.use((req, res) => {
  res.status(404).json({ error: "Not found" });
});

app.use(errorHandler);

export default app;
