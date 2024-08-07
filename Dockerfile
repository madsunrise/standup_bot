FROM python:3.12.4-slim

# Install locales package:
RUN apt-get update && apt-get install -y locales && rm -rf /var/lib/apt/lists/*

# Generate the ru_RU.UTF-8 locale:
RUN sed -i '/ru_RU.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

# Set the locale environment variable
ENV LANG=ru_RU.UTF-8
ENV LANGUAGE=ru_RU:ru
ENV LC_ALL=ru_RU.UTF-8

WORKDIR /app
COPY . .
RUN pip3 install -r requirements.txt
ENTRYPOINT python3 ./main.py

# сборка: docker buildx build --platform linux/amd64 -t standup:latest .
# сохранение: docker save -o standup_latest.tar standup:latest
# выгрузка: docker load -i standup_latest.tar
# запуск docker run --name standup --network=host -d --restart unless-stopped -e TELEGRAM_TARGET_CHAT_ID=0 -e TELEGRAM_BOT_TOKEN=your_token -e TELEGRAM_MAINTAINER_ID=0 standup:latest

# Compose, собрать и запустить: docker-compose up --build standup
# Compose, запустить на сервере: docker-compose up -d (предварительно дописать в docker-compose.yml image: standup:latest)