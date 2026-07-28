import multer from "multer";
import fs from "fs";
import path from "path";

const uploadDir = path.join(process.cwd(), "uploads");

function ensureUploadDir(callback: (error: NodeJS.ErrnoException | null) => void) {
  fs.mkdir(uploadDir, { recursive: true }, callback);
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    ensureUploadDir((error) => {
      cb(error, uploadDir);
    });
  },
  filename: (_req, file, cb) => {
    const timestamp = Date.now();
    const safeName = file.originalname.replace(/[^a-zA-Z0-9.-]/g, "_");
    cb(null, `${timestamp}-${safeName}`);
  },
});

export const avatarUpload = multer({ storage });
