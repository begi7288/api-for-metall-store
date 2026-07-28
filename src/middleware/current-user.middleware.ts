import { NextFunction, Response } from "express";
import type { User } from "@prisma/client";
import type { AuthRequest } from "../types/index.js";
import { AppError } from "../types/index.js";
import { findUserById } from "../services/user.service.js";

export async function attachCurrentUser(req: AuthRequest, res: Response, next: NextFunction) {
  const userId = req.user?.userId;

  if (!userId) {
    throw new AppError("Unauthorized", 401);
  }

  const user = await findUserById(userId);
  if (!user) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  req.currentUser = user as User;
  return next();
}
