# Metal Store API

Production-ready REST API built with Node.js, TypeScript, Express, Prisma, and PostgreSQL.

## Features
- JWT authentication
- Clean architecture: routes, controllers, services, middleware
- Input validation with Zod
- Global error handling
- Password hashing with bcrypt

## Setup
1. Install dependencies:
   ```bash
   npm install
   ```

2. Configure `.env` (use a managed/postgres host in production):
  ```env
  DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/metal_store"
  JWT_SECRET="replace_this_with_a_secure_random_secret"
  JWT_EXPIRES_IN="1h"
  PORT=3000
  ```

3. Generate Prisma client and run migration:
   ```bash
   npm run prisma:generate
   npm run prisma:migrate
   ```

4. Start development server:
   ```bash
   npm run dev
   ```

5. Build for production:
   ```bash
   npm run build
   npm start
   ```

> `npm start` runs in production mode via `NODE_ENV=production`.

## API Endpoints
- `POST /auth/register`
- `POST /auth/login`
- `GET /user/me` (protected)
- `PUT /user/update` (protected)
- `PUT /user/avatar` (protected)
- `PUT /user/change-password` (protected)
- `GET /user/settings` (protected)
- `PUT /user/settings` (protected)

## API Documentation
- Swagger UI available at `http://localhost:3000/docs`

## Docker Setup
1. Copy `.env.example` to `.env` and customize values.
2. Build and start the services:
   ```bash
   docker-compose up --build
   ```
3. API will be available at `http://localhost:3000` (for local Docker). For Render or other cloud deployments, set `DATABASE_URL` to your managed database's connection string and set the required environment variables in the platform dashboard.

Render deployment notes:
- Set environment variables in Render: `DATABASE_URL`, `JWT_SECRET`, `FRONTEND_URL`, etc.
- Use Render build command: `npm install && npm run build` (Render will run `postinstall` which executes `prisma generate`).
- Start command (Render): `npm start` — this runs `node dist/server.js` after build.
- Use Render's Post Deploy hook or `render-postdeploy` to run `prisma migrate deploy` after deployment and before traffic is routed.
- After deployment, ensure migrations have run successfully and your `DATABASE_URL` points to the production database.

## Example API Responses

### `POST /auth/register`
```json
{
  "user": {
    "id": "6b0d1b86-9f25-4dce-b0df-8e3f9d159f40",
    "email": "musojon@example.com",
    "firstName": "Musojon",
    "lastName": "Bek",
    "avatar": "https://example.com/avatar.png",
    "language": "uz",
    "timezone": "Asia/Tashkent",
    "createdAt": "2026-06-28T12:34:56.789Z"
  }
}
```

### `POST /auth/login`
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "6b0d1b86-9f25-4dce-b0df-8e3f9d159f40",
    "firstName": "Musojon",
    "lastName": "Bek",
    "email": "musojon@example.com",
    "avatar": "https://example.com/avatar.png",
    "language": "uz",
    "timezone": "Asia/Tashkent",
    "createdAt": "2026-06-28T12:34:56.789Z"
  }
}
```

### `GET /user/me`
```json
{
  "id": "6b0d1b86-9f25-4dce-b0df-8e3f9d159f40",
  "firstName": "Musojon",
  "lastName": "Bek",
  "email": "musojon@example.com",
  "avatar": "https://example.com/avatar.png",
  "language": "uz",
  "timezone": "Asia/Tashkent",
  "createdAt": "2026-06-28T12:34:56.789Z"
}
```

### `PUT /user/update`
```json
{
  "id": "6b0d1b86-9f25-4dce-b0df-8e3f9d159f40",
  "firstName": "Musojon",
  "lastName": "Bek",
  "email": "musojon@example.com",
  "avatar": "https://example.com/avatar.png",
  "language": "uz",
  "timezone": "Asia/Tashkent",
  "createdAt": "2026-06-28T12:34:56.789Z"
}
```

### `PUT /user/avatar`
```json
{
  "avatar": "/uploads/1688000000000-avatar.png"
}
```

### `PUT /user/change-password`
```json
{
  "message": "Password changed successfully"
}
```

### `GET /user/settings`
```json
{
  "language": "uz",
  "timezone": "Asia/Tashkent"
}
```

### `PUT /user/settings`
```json
{
  "language": "ru",
  "timezone": "Europe/Moscow"
}
```
```