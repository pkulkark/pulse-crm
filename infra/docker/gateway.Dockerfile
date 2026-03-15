FROM node:22-alpine

WORKDIR /workspace

COPY package.json nx.json eslint.config.mjs .prettierrc.json ./
COPY apps/frontend/package.json apps/frontend/package.json
COPY apps/gateway/package.json apps/gateway/package.json

RUN npm install

COPY apps/gateway apps/gateway

EXPOSE 4000

CMD ["npm", "run", "start", "--workspace", "@samplecrm/gateway"]

