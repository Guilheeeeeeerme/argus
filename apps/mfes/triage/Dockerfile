FROM node:22-alpine
WORKDIR /app
COPY package.json tsconfig.json vite.config.ts index.html ./
COPY src ./src
RUN npm install
EXPOSE 3001
CMD ["npm", "run", "dev", "--", "--port", "3001"]
