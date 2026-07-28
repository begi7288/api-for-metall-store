const swaggerServerUrl = process.env.SWAGGER_SERVER_URL ?? "/";

const swaggerDocument = {
  openapi: "3.0.0",
  info: {
    title: "Metal Store API",
    description: "REST API for user authentication and profile management.",
    version: "1.0.0",
  },
  servers: [
    {
      url: swaggerServerUrl,
      description: "API server",
    },
  ],
  components: {
    securitySchemes: {
      bearerAuth: {
        type: "http",
        scheme: "bearer",
        bearerFormat: "JWT",
      },
    },
    schemas: {
      RegisterRequest: {
        type: "object",
        properties: {
          firstName: { type: "string", example: "Musojon" },
          lastName: { type: "string", example: "Bek" },
          email: { type: "string", format: "email", example: "musojon@example.com" },
          password: { type: "string", format: "password", example: "P@ssw0rd!" },
          avatar: { type: "string", format: "uri", example: "https://example.com/avatar.png" },
          language: { type: "string", example: "uz" },
          timezone: { type: "string", example: "Asia/Tashkent" },
        },
        required: ["firstName", "lastName", "email", "password"],
      },
      LoginRequest: {
        type: "object",
        properties: {
          email: { type: "string", format: "email", example: "musojon@example.com" },
          password: { type: "string", format: "password", example: "P@ssw0rd!" },
        },
        required: ["email", "password"],
      },
      LoginResponse: {
        type: "object",
        properties: {
          token: { type: "string" },
          user: { $ref: "#/components/schemas/UserResponse" },
        },
      },
      UserResponse: {
        type: "object",
        properties: {
          id: { type: "string", format: "uuid" },
          firstName: { type: "string" },
          lastName: { type: "string" },
          email: { type: "string", format: "email" },
          avatar: { type: "string", nullable: true },
          language: { type: "string" },
          timezone: { type: "string" },
          createdAt: { type: "string", format: "date-time" },
        },
      },
      AvatarResponse: {
        type: "object",
        properties: {
          avatar: { type: "string" },
        },
      },
      MessageResponse: {
        type: "object",
        properties: {
          message: { type: "string" },
        },
      },
      SettingsResponse: {
        type: "object",
        properties: {
          language: { type: "string", example: "uz" },
          timezone: { type: "string", example: "Asia/Tashkent" },
        },
      },
      UserSettingsRequest: {
        type: "object",
        properties: {
          language: { type: "string", example: "uz" },
          timezone: { type: "string", example: "Asia/Tashkent" },
        },
      },
      ChangePasswordRequest: {
        type: "object",
        properties: {
          oldPassword: { type: "string", format: "password", example: "P@ssw0rd!" },
          newPassword: { type: "string", format: "password", example: "NewP@ssw0rd!" },
          confirmPassword: { type: "string", format: "password", example: "NewP@ssw0rd!" },
        },
        required: ["oldPassword", "newPassword", "confirmPassword"],
      },
      UpdateNameRequest: {
        type: "object",
        properties: {
          firstName: { type: "string", example: "Musojon" },
          lastName: { type: "string", example: "Bek" },
        },
        required: ["firstName", "lastName"],
      },
      UpdateAvatarRequest: {
        type: "object",
        properties: {
          avatarUrl: { type: "string", format: "uri", example: "https://example.com/avatar.png" },
        },
      },
    },
  },
  paths: {
    "/auth/register": {
      post: {
        tags: ["Auth"],
        summary: "Register a new user",
        requestBody: {
          required: true,
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/RegisterRequest" },
            },
          },
        },
        responses: {
          "201": {
            description: "User created",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/UserResponse" },
              },
            },
          },
          "409": { description: "Email already exists" },
        },
      },
    },
    "/auth/login": {
      post: {
        tags: ["Auth"],
        summary: "Login with email and password",
        requestBody: {
          required: true,
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/LoginRequest" },
            },
          },
        },
        responses: {
          "200": {
            description: "Login successful",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/LoginResponse" },
              },
            },
          },
          "401": { description: "Invalid credentials" },
        },
      },
    },
    "/user/me": {
      get: {
        tags: ["User"],
        summary: "Get current user profile",
        security: [{ bearerAuth: [] }],
        responses: {
          "200": {
            description: "Current user profile",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/UserResponse" },
              },
            },
          },
          "401": { description: "Unauthorized" },
        },
      },
    },
    "/user/update": {
      put: {
        tags: ["User"],
        summary: "Update user first and last name",
        security: [{ bearerAuth: [] }],
        requestBody: {
          required: true,
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/UpdateNameRequest" },
            },
          },
        },
        responses: {
          "200": {
            description: "Updated user profile",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/UserResponse" },
              },
            },
          },
          "401": { description: "Unauthorized" },
        },
      },
    },
    "/user/avatar": {
      put: {
        tags: ["User"],
        summary: "Update user avatar URL or upload file",
        security: [{ bearerAuth: [] }],
        requestBody: {
          required: false,
          content: {
            "multipart/form-data": {
              schema: {
                type: "object",
                properties: {
                  avatar: { type: "string", format: "binary" },
                  avatarUrl: { type: "string", format: "uri" },
                },
              },
            },
            "application/json": {
              schema: { $ref: "#/components/schemas/UpdateAvatarRequest" },
            },
          },
        },
        responses: {
          "200": {
            description: "Updated avatar",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/AvatarResponse" },
              },
            },
          },
          "400": { description: "Bad request" },
          "401": { description: "Unauthorized" },
        },
      },
    },
    "/user/change-password": {
      put: {
        tags: ["User"],
        summary: "Change user password",
        security: [{ bearerAuth: [] }],
        requestBody: {
          required: true,
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/ChangePasswordRequest" },
            },
          },
        },
        responses: {
          "200": {
            description: "Password changed successfully",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/MessageResponse" },
              },
            },
          },
          "400": { description: "Validation error or incorrect old password" },
          "401": { description: "Unauthorized" },
        },
      },
    },
    "/user/settings": {
      get: {
        tags: ["User"],
        summary: "Get current user settings",
        security: [{ bearerAuth: [] }],
        responses: {
          "200": {
            description: "User settings",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/SettingsResponse" },
              },
            },
          },
          "401": { description: "Unauthorized" },
        },
      },
      put: {
        tags: ["User"],
        summary: "Update user settings",
        security: [{ bearerAuth: [] }],
        requestBody: {
          required: true,
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/UserSettingsRequest" },
            },
          },
        },
        responses: {
          "200": {
            description: "Updated settings",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/SettingsResponse" },
              },
            },
          },
          "401": { description: "Unauthorized" },
        },
      },
    },
  },
};

export default swaggerDocument;
