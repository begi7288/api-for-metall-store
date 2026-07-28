import { Request, Response } from "express";
import { loginUser, registerUser } from "../services/auth.service.js";

export async function registerController(req: Request, res: Response) {
  const user = await registerUser(req.body);
  res.status(201).json({ data: { user } });
}

export async function loginController(req: Request, res: Response) {
  const payload = await loginUser(req.body);
  res.status(200).json({ data: payload });
}
