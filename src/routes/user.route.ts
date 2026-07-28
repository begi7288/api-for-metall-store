import { Router } from "express";
import { authenticateToken } from "../middleware/auth.middleware.js";
import { avatarUpload } from "../middleware/upload.middleware.js";
import {
  getProfileController,
  updateProfileController,
  updateAvatarController,
  changePasswordController,
  getSettingsController,
  updateSettingsController,
} from "../controllers/user.controller.js";
import { validate } from "../middleware/validate.middleware.js";
import { updateNameSchema, updateAvatarSchema, changePasswordSchema, userSettingsSchema } from "../schemas/user.schema.js";
import { asyncHandler } from "../utils/asyncHandler.js";

const router = Router();

const authStack = [authenticateToken];

router.get("/me", authStack, asyncHandler(getProfileController));
router.put("/update", authStack, validate(updateNameSchema), asyncHandler(updateProfileController));
router.put(
  "/avatar",
  authStack,
  avatarUpload.single("avatar"),
  validate(updateAvatarSchema),
  asyncHandler(updateAvatarController),
);
router.put("/change-password", authStack, validate(changePasswordSchema), asyncHandler(changePasswordController));
router.get("/settings", authStack, asyncHandler(getSettingsController));
router.put("/settings", authStack, validate(userSettingsSchema), asyncHandler(updateSettingsController));

export default router;
