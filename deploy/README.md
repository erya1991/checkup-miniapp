# Deploy

部署相关目录。

Stage 01 本地 PostgreSQL 17 Compose 文件位于仓库根目录 `compose.yaml`，以便直接执行 `docker compose`。复制根目录 `.env.example` 为 `.env` 并设置本地开发凭据，然后在仓库根目录执行 `docker compose up -d postgres` 和 `docker compose ps`。数据保存在命名 volume `postgres_data`。生产 Nginx/HTTPS 不属于本阶段。

Stage 05 新增同 backend codebase 的独立清理进程（无需新中间件）：目标环境先执行 migration 至 `0005_report_management` 并重启 API，在另一个终端持续运行 `python -m app.cleanup_worker`（本地使用 `backend/.venv/Scripts/python.exe`，cwd 为 backend）。API、OCR Worker、cleanup worker 均需运行；现有 Compose 仍只负责本地 PostgreSQL。生产进程托管由目标部署方式负责，不在本轮自行扩展部署体系。cleanup 使用现有 DATABASE_URL 与私有 COS 配置，云账户需 ListObjects/DeleteObject 权限。PREFIX 删除失败持久保留 PENDING，每 10 秒重试；不得在消费者未运行时宣称文件最终已清理。
