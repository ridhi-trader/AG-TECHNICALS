FROM python:3.12-slim

# Install nginx
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

# Install Python deps
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

# Copy all files
COPY . .

# Nginx config — serve HTML on port 80, proxy /api/* to FastAPI on 8000
RUN cat > /etc/nginx/sites-available/default << 'NGINX'
server {
    listen 3000;
    root /app;
    index index.html;

    # Serve static files
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API calls to FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX

# Start script — run both nginx and FastAPI
RUN echo '#!/bin/bash\nuvicorn chat_backend:app --host 127.0.0.1 --port 8000 &\nnginx -g "daemon off;"' > /start.sh && chmod +x /start.sh

EXPOSE 3000
CMD ["/start.sh"]
