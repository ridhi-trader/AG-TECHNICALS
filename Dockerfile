FROM python:3.12-slim

# Install nginx
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

# Install Python deps
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

# Copy all files
COPY . .

# Nginx config
RUN printf 'server {\n    listen 3000;\n    root /app;\n    index index.html;\n    location / {\n        try_files $uri $uri.html $uri/ /index.html;\n    }\n    location /api/ {\n        proxy_pass http://127.0.0.1:8000/api/;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_read_timeout 60s;\n    }\n}\n' > /etc/nginx/sites-available/default

# Copy and set permissions for start script
RUN chmod +x /app/start.sh

EXPOSE 3000
CMD ["/app/start.sh"]
