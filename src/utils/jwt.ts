import jwt, { SignOptions, VerifyOptions } from "jsonwebtoken";
import { env } from "../config/index.js";
import type { JwtPayload } from "../types/index.js";

const jwtOptions: SignOptions = {
  expiresIn: env.jwtExpiresIn as SignOptions["expiresIn"],
  algorithm: "HS256",
};

const jwtVerifyOptions: VerifyOptions = {
  algorithms: ["HS256"],
};

export function signToken(payload: JwtPayload): string {
  return jwt.sign(payload, env.jwtSecret, jwtOptions);
}

export function verifyToken(token: string): JwtPayload {
  return jwt.verify(token, env.jwtSecret, jwtVerifyOptions) as JwtPayload;
}
