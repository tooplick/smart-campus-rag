# 前端镜像:node 构建静态资源 → nginx 托管(SPA 回退)
FROM node:24-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# 顶层 nginx 以 frontend:5173 上游转发,故此处监听 5173 保持一致
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 5173
