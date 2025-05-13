 FROM python:3.11-alpine

ARG TERMINUS_VERSION=3.6.2

RUN apk update && apk add --no-cache php php-cli php-phar php-mbstring php-openssl \
    php-json php-tokenizer php-xml php-dom composer

RUN composer global require pantheon-systems/terminus:$TERMINUS_VERSION

ENV PATH="/root/.composer/vendor/bin:${PATH}"

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY terminus_env_metrics_exporter.py .

ENTRYPOINT ["python", "terminus_env_metrics_exporter.py"]
