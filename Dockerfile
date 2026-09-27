# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/contracts/package.json packages/contracts/package.json
COPY packages/db/package.json packages/db/package.json
RUN npm ci

FROM node:22-bookworm-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build && npm run build:cli

FROM node:22-bookworm-slim AS runtime
ARG GIT_COMMIT=unknown
ARG BUILD_TIME=unknown
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0 \
    PDOOM_MIGRATIONS_DIR=/app/migrations \
    GIT_COMMIT=${GIT_COMMIT} \
    BUILD_TIME=${BUILD_TIME}
LABEL org.opencontainers.image.title="pdoom-live" \
      org.opencontainers.image.source="https://github.com/mishakgg/pdoom-live" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.created="${BUILD_TIME}"
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1001 pdoom \
    && useradd --uid 1001 --gid pdoom --home-dir /app --no-create-home --shell /usr/sbin/nologin pdoom
COPY --from=build --chown=pdoom:pdoom /app/apps/web/.next/standalone ./
COPY --from=build --chown=pdoom:pdoom /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=build --chown=pdoom:pdoom /app/packages/db/migrations ./migrations
COPY --from=build --chown=pdoom:pdoom /app/dist/pdoom-cli.mjs ./pdoom-cli.mjs
USER pdoom
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:'+(process.env.PORT||3000)+'/api/ready').then((response)=>process.exit(response.ok?0:1)).catch(()=>process.exit(1))"]
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["node", "apps/web/server.js"]
