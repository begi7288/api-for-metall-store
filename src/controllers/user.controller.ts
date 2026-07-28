import { Response } from "express";
import type { AuthRequest } from "../types/index.js";
import { AppError } from "../types/index.js";
import { comparePassword, hashPassword } from "../utils/password.js";
import { updateUserAvatar, updateUserName, updateUserPassword, updateUserSettings } from "../services/user.service.js";
import { UpdateNameInput, UpdateAvatarInput, ChangePasswordInput, UserSettingsInput } from "../schemas/user.schema.js";

function serializeUser(user: NonNullable<AuthRequest["currentUser"]>) {
  return {
    id: user.id,
    firstName: user.firstName,
    lastName: user.lastName,
    email: user.email,
    avatar: user.avatar,
    language: user.language,
    timezone: user.timezone,
    createdAt: user.createdAt,
  };
}

export async function getProfileController(req: AuthRequest, res: Response) {
  const user = req.currentUser;
  if (!user) {
    throw new AppError("Unauthorized", 401);
  }

  return res.status(200).json(serializeUser(user));
}

export async function updateProfileController(req: AuthRequest, res: Response) {
  const user = req.currentUser;
  if (!user) {
    throw new AppError("Unauthorized", 401);
  }

  const { firstName, lastName } = req.body as UpdateNameInput;
  const updated = await updateUserName(user.id, firstName, lastName);

  return res.status(200).json(serializeUser(updated));
}

export async function updateAvatarController(req: AuthRequest, res: Response) {
  const user = req.currentUser;
  if (!user) {
    throw new AppError("Unauthorized", 401);
  }

  const body = req.body as UpdateAvatarInput;
  const avatarUrl = body.avatarUrl?.trim();
  const filePath = req.file ? `/uploads/${req.file.filename}` : undefined;

  const avatar = filePath || avatarUrl;
  if (!avatar) {
    throw new AppError("Avatar file or URL is required", 400);
  }

  const updated = await updateUserAvatar(user.id, avatar);
  return res.status(200).json({ avatar: updated.avatar });
}

export async function getSettingsController(req: AuthRequest, res: Response) {
  const user = req.currentUser;
  if (!user) {
    throw new AppError("Unauthorized", 401);
  }

  return res.status(200).json({
    language: user.language,
    timezone: user.timezone,
  });
}

export async function updateSettingsController(req: AuthRequest, res: Response) {
  const user = req.currentUser;
  if (!user) {
    throw new AppError("Unauthorized", 401);
  }

  const settings = req.body as UserSettingsInput;
  const updated = await updateUserSettings(user.id, settings);

  return res.status(200).json({
    language: updated.language,
    timezone: updated.timezone,
  });
}

export async function changePasswordController(req: AuthRequest, res: Response) {
  const user = req.currentUser;
  if (!user) {
    throw new AppError("Unauthorized", 401);
  }

  const { oldPassword, newPassword } = req.body as ChangePasswordInput;
  const oldPasswordMatches = await comparePassword(oldPassword, user.password);

  if (!oldPasswordMatches) {
    throw new AppError("Old password is incorrect", 400);
  }

  const passwordHash = await hashPassword(newPassword);
  await updateUserPassword(user.id, passwordHash);

  return res.status(200).json({ message: "Password changed successfully" });
}
