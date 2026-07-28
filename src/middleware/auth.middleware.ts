import { NextFunction, Request, Response } from "express";
import jwt from "jsonwebtoken";
import { findUserById } from "../services/user.service.js";
import { verifyToken } from "../utils/jwt.js";
import type { AuthRequest, JwtPayload } from "../types/index.js";

export async function authenticateToken(req: AuthRequest, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  const token = authHeader?.startsWith("Bearer ") ? authHeader.slice(7).trim() : undefined;

  if (!token) {
    return res.status(401).json({ error: "Authorization token missing" });
  }

  try {
    const payload = verifyToken(token);
    req.user = payload;

    const user = await findUserById(payload.userId);
    if (!user) {
      return res.status(403).json({ error: "Forbidden: user no longer exists." });
    }

    req.currentUser = user;
    return next();
  } catch (error) {
    if (error instanceof jwt.TokenExpiredError) {
      return res.status(401).json({ error: "Token expired" });
    }

    if (error instanceof jwt.JsonWebTokenError) {
      return res.status(401).json({ error: "Invalid token" });
    }

    return res.status(401).json({ error: "Authentication failed" });
  }
}
