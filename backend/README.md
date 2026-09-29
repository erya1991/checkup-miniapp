# Backend（Stage 01）

仅提供 FastAPI 健康检查、基础日志/错误响应、SQLAlchemy 连接和空表 Alembic 迁移；没有业务模型。

在仓库根目录复制 `.env.example` 为不提交的 `.env`，为本机开发设置 `POSTGRES_*` 与一致的 `DATABASE_URL`。先运行 `docker compose up -d postgres`。

PowerShell（在 `backend/`）：

```powershell
& 'C:\Users\65410\AppData\Local\Programs\Python\Python312\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

第一行解释器路径是本次开发机的实测位置；其它开发机请替换为自己的 Python 3.12.x 路径。访问 `http://127.0.0.1:8000/api/v1/health`。

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
```

配置读取仓库根目录 `.env` 或进程环境变量；`DATABASE_URL` 必填。初始迁移只建立 Alembic 版本记录，不创建业务表。
