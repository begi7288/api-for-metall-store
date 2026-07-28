FROM node:20-alpine AS builder
WORKDIR /usr/src/app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN mkdir -p uploads
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /usr/src/app
COPY package.json package-lock.json ./
ENV NODE_ENV=production
# Install runtime system libs required by Prisma (libssl, CA certs, glibc helpers)
# Keep the image small by using --no-cache and installing only runtime packages.
RUN apk add --no-cache openssl ca-certificates libgcc libstdc++ \
	&& update-ca-certificates || true

# Install production node modules
RUN npm install --production
COPY --from=builder /usr/src/app/dist ./dist
COPY --from=builder /usr/src/app/uploads ./uploads
COPY --from=builder /usr/src/app/prisma ./prisma
EXPOSE 3000
CMD ["npm", "start"]
