import type { Request } from "express";
import type { User } from "@prisma/client";

export interface JwtPayload {
  userId: string;
}

export interface AuthRequest extends Request {
  user?: JwtPayload;
  currentUser?: User;
  file?: Express.Multer.File;
}

export interface HttpError extends Error {
  status?: number;
  statusCode?: number;
}

export class AppError extends Error {
  public readonly status: number;
  public readonly statusCode: number;

  constructor(message: string, status = 500) {
    super(message);
    this.status = status;
    this.statusCode = status;
    Error.captureStackTrace(this, this.constructor);
  }
}
