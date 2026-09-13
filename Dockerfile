FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

RUN echo 'server {
    listen 3000;
    root /app;
    index index.html;
    client_max_body_size 100M;

    location / {
        try_files $uri $uri.html $uri/ =404;
    }

    location /uploaded_files/ {
        alias /var/data/uploaded_files/;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
        client_max_body_size 100M;
    }
}' > /etc/nginx/sites-available/default

RUN ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default \
    && rm -f /etc/nginx/sites-enabled/default.bak \
    && nginx -t

RUN mkdir -p /var/data/uploaded_files && chmod +x /app/start.sh

EXPOSE 3000
CMD ["/app/start.sh"]
