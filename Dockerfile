FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

RUN printf 'server {\n\
    listen 3000;\n\
    root /app;\n\
    index index.html;\n\
    client_max_body_size 100M;\n\
    location / {\n\
        try_files $uri $uri.html $uri/ /index.html;\n\
    }\n\
    location /uploaded_files/ {\n\
        alias /var/data/uploaded_files/;\n\
    }\n\
    location /api/ {\n\
        proxy_pass http://127.0.0.1:8000/api/;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_read_timeout 300s;\n\
        client_max_body_size 100M;\n\
    }\n\
}\n' > /etc/nginx/sites-available/default

RUN mkdir -p /var/data/uploaded_files && chmod +x /app/start.sh

EXPOSE 3000
CMD ["/app/start.sh"]
