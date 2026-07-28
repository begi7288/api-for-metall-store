import { z } from "zod";

export const updateNameSchema = z.object({
  firstName: z.string().min(1, "First name is required"),
  lastName: z.string().min(1, "Last name is required"),
});

export const updateAvatarSchema = z.object({
  avatarUrl: z.string().url("Avatar must be a valid URL").optional(),
});

export const userSettingsSchema = z
  .object({
    language: z.string().min(1, "Language is required").optional(),
    timezone: z.string().min(1, "Timezone is required").optional(),
  })
  .refine((data) => data.language !== undefined || data.timezone !== undefined, {
    message: "At least one setting must be provided",
  });

export const changePasswordSchema = z.object({
  oldPassword: z.string().min(1, "Old password is required"),
  newPassword: z.string()
    .min(8, "New password must be at least 8 characters")
    .regex(/[A-Z]/, "New password must contain at least one uppercase letter")
    .regex(/[a-z]/, "New password must contain at least one lowercase letter")
    .regex(/[0-9]/, "New password must contain at least one number")
    .regex(/[^A-Za-z0-9]/, "New password must contain at least one special character"),
  confirmPassword: z.string().min(1, "Confirm password is required"),
}).refine((data) => data.newPassword === data.confirmPassword, {
  path: ["confirmPassword"],
  message: "Passwords do not match",
});

export type UpdateNameInput = z.infer<typeof updateNameSchema>;
export type UpdateAvatarInput = z.infer<typeof updateAvatarSchema>;
export type ChangePasswordInput = z.infer<typeof changePasswordSchema>;
export type UserSettingsInput = z.infer<typeof userSettingsSchema>;
