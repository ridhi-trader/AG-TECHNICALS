FROM python:3.12-slim-bookworm

ARG CACHE_BUST=1
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

RUN cp /app/nginx.conf /etc/nginx/sites-available/default \
    && ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default \
    && nginx -t

RUN mkdir -p /var/data/uploaded_files && chmod +x /app/start.sh

EXPOSE 3000
CMD ["/app/start.sh"]
