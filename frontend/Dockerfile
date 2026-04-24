# Build stage
FROM node:18-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# Production stage
FROM nginx:alpine

LABEL org.opencontainers.image.source="https://github.com/AtsushiUtsumi/lightsail-test"

COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
