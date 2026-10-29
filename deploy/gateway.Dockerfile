FROM node:22-alpine@sha256:fe4f6d74e20370acb04ad889077d14d0f64a9c8ea6a42bc60cddf1e844699914
WORKDIR /app
COPY --chown=node:node gateway/server.mjs /app/gateway/server.mjs
USER node
ENV GATEWAY_HOST=0.0.0.0 GATEWAY_PORT=3000
EXPOSE 3000
CMD ["node", "gateway/server.mjs"]
