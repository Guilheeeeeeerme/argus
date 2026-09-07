FROM node:22-alpine
WORKDIR /app
COPY package.json ./
EXPOSE 8180
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0 --port 8180"]
