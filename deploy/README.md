# Deploy

部署相关目录。

Stage 01 本地 PostgreSQL 17 Compose 文件位于仓库根目录 `compose.yaml`，以便直接执行 `docker compose`。复制根目录 `.env.example` 为 `.env` 并设置本地开发凭据，然后在仓库根目录执行 `docker compose up -d postgres` 和 `docker compose ps`。数据保存在命名 volume `postgres_data`。生产 Nginx/HTTPS 不属于本阶段。
