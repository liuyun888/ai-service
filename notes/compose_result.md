# 13.01 容器化编排 · 验收笔记

## 文件检查
- Dockerfile / compose / .dockerignore / lifecycle：`True`
- healthcheck：`True`；stop_grace_period：`True`
- .dockerignore 排除 .env：`True`

## Compose 服务
- services：`['ai-service']`
- ports：`['${APP_PORT:-8091}:8091']`
- grace：`25s`

## Docker
- available：`False` config_ok=`docker not installed`

## Health
- reachable：`True` body=`{'status': 'ok', 'app': 'ai-service'}`

## 常用命令
```bash
cd ai-service
docker compose up -d --build
curl -f http://127.0.0.1:8091/health
docker compose down
```

密钥：只放 `.env`，已在 `.dockerignore` 排除；不要 COPY 进镜像。

SUMMARY: compose 验收通过（无 Docker 时以文件+YAML 为准）
