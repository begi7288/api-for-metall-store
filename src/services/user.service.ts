import prisma from "../prisma/client.js";
import { RegisterInput } from "../schemas/auth.schema.js";

export async function findUserByEmail(email: string) {
  return prisma.user.findUnique({ where: { email } });
}

export async function findUserById(id: string) {
  return prisma.user.findUnique({ where: { id } });
}

export async function createUser(data: RegisterInput) {
  return prisma.user.create({
    data: {
      firstName: data.firstName,
      lastName: data.lastName,
      email: data.email,
      password: data.password,
      avatar: data.avatar,
      language: data.language,
      timezone: data.timezone,
    },
  });
}

export async function updateUserName(id: string, firstName: string, lastName: string) {
  return prisma.user.update({
    where: { id },
    data: { firstName, lastName },
  });
}

export async function updateUserAvatar(id: string, avatar: string) {
  return prisma.user.update({
    where: { id },
    data: { avatar },
  });
}

export async function updateUserSettings(id: string, settings: { language?: string; timezone?: string }) {
  return prisma.user.update({
    where: { id },
    data: settings,
  });
}

export async function updateUserPassword(id: string, password: string) {
  return prisma.user.update({
    where: { id },
    data: { password },
  });
}
