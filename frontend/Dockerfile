FROM node:20-alpine

WORKDIR /app

# Nur package files kopieren für schnelleres Caching
COPY package*.json ./
RUN npm install

# Restlichen Code kopieren
COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL


EXPOSE 5173

CMD ["npm", "run", "dev"]