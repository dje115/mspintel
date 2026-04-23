FROM node:20-alpine

# Use /src (not /app): Vite must serve SPA routes like GET /app without colliding with the
# container filesystem root named "app" (EISDIR when the dev server tries to read `/app`).
WORKDIR /src

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# With Compose bind-mounting ./frontend over /src, /src/node_modules often lives in a
# separate volume; run install on start so new deps (e.g. qrcode.react) are always present.
CMD ["sh", "-c", "npm install && npm run dev"]
