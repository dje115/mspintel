# Debian slim (glibc): Vite/Rollup need a matching native Rollup binary inside Linux containers.
# Alpine (musl) plus npm optional-deps edge cases often produced MODULE_NOT_FOUND for
# @rollup/rollup-linux-x64-musl when /src/node_modules is on a persisted volume.
FROM node:20-bookworm-slim

# Use /src (not /app): Vite must serve SPA routes like GET /app without colliding with the
# container filesystem root named "app" (EISDIR when the dev server tries to read `/app`).
WORKDIR /src

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# With Compose bind-mounting ./frontend over /src, /src/node_modules lives on a named volume;
# run install on start so new deps are always present for the mounted source tree.
CMD ["sh", "-c", "npm install && npm run dev"]
