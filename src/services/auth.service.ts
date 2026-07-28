import { comparePassword, hashPassword } from "../utils/password.js";
import { findUserByEmail, createUser } from "./user.service.js";
import { LoginInput, RegisterInput } from "../schemas/auth.schema.js";
import { Prisma } from "@prisma/client";
import { signToken } from "../utils/jwt.js";
import { AppError } from "../types/index.js";

export async function registerUser(input: RegisterInput) {
  const existing = await findUserByEmail(input.email);

  if (existing) {
    throw new AppError("Email already exists", 409);
  }

  const passwordHash = await hashPassword(input.password);

  let user;
  try {
    user = await createUser({ ...input, password: passwordHash });
  } catch (error) {
    if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2002") {
      throw new AppError("Email already exists", 409);
    }
    throw error;
  }

  return {
    id: user.id,
    email: user.email,
    firstName: user.firstName,
    lastName: user.lastName,
    avatar: user.avatar,
    language: user.language,
    timezone: user.timezone,
    createdAt: user.createdAt,
  };
}

export async function loginUser(input: LoginInput) {
  const user = await findUserByEmail(input.email);

  if (!user) {
    throw new AppError("Invalid credentials", 401);
  }

  const isValid = await comparePassword(input.password, user.password);
  if (!isValid) {
    throw new AppError("Invalid credentials", 401);
  }

  const token = signToken({ userId: user.id });

  return {
    token,
    user: {
      id: user.id,
      firstName: user.firstName,
      lastName: user.lastName,
      email: user.email,
      avatar: user.avatar,
      language: user.language,
      timezone: user.timezone,
      createdAt: user.createdAt,
    },
  };
}
