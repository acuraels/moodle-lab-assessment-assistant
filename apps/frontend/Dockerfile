FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_ENABLE_TEST_LOGIN=false
ENV VITE_API_BASE_URL=/api \
    VITE_ENABLE_TEST_LOGIN=${VITE_ENABLE_TEST_LOGIN}
RUN npm run build

FROM nginx:1.28-alpine AS runtime
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
