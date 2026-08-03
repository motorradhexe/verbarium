# Development image — runs the Vite dev server with hot reload.
# A production build (nginx serving `npm run build` output) comes later.
FROM node:24-alpine

WORKDIR /app

# Install from the lockfile so container and host resolve identical versions.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
