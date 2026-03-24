FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN if [ -f package.json ]; then npm install; else echo "No package.json yet"; fi

COPY . .

EXPOSE 5173
CMD ["sh", "-c", "if [ -f package.json ]; then npm run dev -- --host 0.0.0.0 --port 5173; else echo 'Frontend scaffold ready'; sleep infinity; fi"]
