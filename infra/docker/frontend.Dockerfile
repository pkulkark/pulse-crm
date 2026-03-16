FROM node:22-alpine

WORKDIR /workspace

COPY package.json nx.json eslint.config.mjs .prettierrc.json ./
COPY apps/frontend/package.json apps/frontend/package.json
COPY apps/gateway/package.json apps/gateway/package.json

RUN npm install

COPY apps/frontend apps/frontend

EXPOSE 3000

CMD ["npm", "run", "dev", "--workspace", "@pulsecrm/frontend", "--", "--host", "0.0.0.0", "--port", "3000"]
