# ai-service 镜像：课次 13.01
# 密钥不要写进本文件；用 compose 的 env_file / environment 注入。

FROM python:3.12-slim

# 健康检查需要 curl（slim 默认没有）
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖，利用层缓存（改代码不必重装包）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 容器内监听；宿主机映射见 docker-compose.yml（默认 8091）
ENV APP_PORT=8091
EXPOSE 8091

# --timeout-graceful-shutdown：收到 SIGTERM 后给进行中的请求收尾的秒数
# 与 compose 的 stop_grace_period 配合，先优雅再强制
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT:-8091} --timeout-graceful-shutdown 20"]
