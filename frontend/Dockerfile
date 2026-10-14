FROM node:20-slim

# System-Abhängigkeiten für Rust & WASM installieren
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Rust & wasm-pack installieren
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cargo install wasm-pack


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