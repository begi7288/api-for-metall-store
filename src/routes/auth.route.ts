import { Router } from "express";
import { loginController, registerController } from "../controllers/auth.controller.js";
import { validate } from "../middleware/validate.middleware.js";
import { loginSchema, registerSchema } from "../schemas/auth.schema.js";
import { asyncHandler } from "../utils/asyncHandler.js";

const router = Router();

router.post("/register", validate(registerSchema), asyncHandler(registerController));
router.post("/login", validate(loginSchema), asyncHandler(loginController));

export default router;
