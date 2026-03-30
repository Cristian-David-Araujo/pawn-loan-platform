FROM node:20-alpine

WORKDIR /app

EXPOSE 5173

CMD ["sh", "-c", "if [ -f package.json ]; then npm install && npm run dev -- --host 0.0.0.0 --port 5173; else echo 'Missing package.json in /app'; tail -f /dev/null; fi"]
