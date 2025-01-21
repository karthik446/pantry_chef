FROM --platform=linux/arm64/v8 node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 8000

CMD ["npm", "start"]