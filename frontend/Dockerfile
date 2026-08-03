# Development image — runs the Vite dev server with hot reload.
# A production build (nginx serving `npm run build` output) comes later.
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
