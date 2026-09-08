FROM node:22-alpine
WORKDIR /app
COPY package.json ./
EXPOSE 8181
CMD ["sh", "-c", "npm ci && npm run dev -- --host 0.0.0.0 --port 8181"]
