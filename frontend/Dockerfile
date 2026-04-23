FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# With Compose bind-mounting ./frontend over /app, /app/node_modules often lives in a
# separate volume; run install on start so new deps (e.g. qrcode.react) are always present.
CMD ["sh", "-c", "npm install && npm run dev"]
