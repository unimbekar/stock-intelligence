FROM node:22-bookworm-slim
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web ./
COPY packages/config/product.json /app/product.json
ENV PRODUCT_CONFIG_PATH=/app/product.json
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
