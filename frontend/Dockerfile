# Debian slim (glibc): Vite/Rollup need a matching native Rollup binary inside Linux containers.
# Alpine (musl) plus npm optional-deps edge cases often produced MODULE_NOT_FOUND for
# @rollup/rollup-linux-x64-musl when /src/node_modules is on a persisted volume.
FROM node:20-bookworm-slim

# Use /src (not /app): Vite must serve SPA routes like GET /app without colliding with the
# container filesystem root named "app" (EISDIR when the dev server tries to read `/app`).
WORKDIR /src

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libcairo2 \
        libcups2 \
        libdbus-1-3 \
        libdrm2 \
        libfontconfig1 \
        libgbm1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libx11-6 \
        libx11-xcb1 \
        libxcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
        libxrender1 \
        libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# With Compose bind-mounting ./frontend over /src, /src/node_modules lives on a named volume;
# run install on start so new deps are always present for the mounted source tree.
CMD ["sh", "-c", "npm install && npm run dev"]
