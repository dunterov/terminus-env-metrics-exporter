FROM python:3.11-alpine

# https://github.com/pantheon-systems/terminus/releases
ARG TERMINUS_VERSION=4.0.1

RUN apk update && apk add --no-cache php php-cli php-phar php-mbstring php-openssl \
    php-json php-tokenizer php-xml php-dom composer

RUN composer global require pantheon-systems/terminus:$TERMINUS_VERSION

ENV PATH="/root/.composer/vendor/bin:${PATH}"

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY terminus_env_metrics_exporter.py .

ENTRYPOINT ["python", "terminus_env_metrics_exporter.py"]
