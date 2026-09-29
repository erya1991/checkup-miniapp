# Backend（Stage 02）

提供健康检查、微信 code 登录、系统 Token、健康档案、报告导入和 COS 原图资产 API。迁移 `0002_profile_upload` 建立四张核心表及上传授权、文件清理记录表。本阶段到 ingestion READY，不执行 OCR。

在仓库根目录复制 `.env.example` 为不提交的 `.env`，设置 `POSTGRES_*` 与一致的 `DATABASE_URL`，以及至少 32 字符的 `JWT_SECRET`、微信 `WECHAT_APP_ID` / `WECHAT_APP_SECRET`、私有 COS 的 `COS_SECRET_ID` / `COS_SECRET_KEY` / `COS_BUCKET` / `COS_REGION`。先运行 `docker compose up -d postgres`。永久密钥不得进入 Git 或小程序。

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

配置读取仓库根目录 `.env` 或进程环境变量；`DATABASE_URL` 必填。自动测试 mock 微信身份交换和 COS 服务端操作，不请求真实外网。COS 授权仅对一个随机 object key 开放 15 分钟 PutObject；登记时后端 HEAD 验证对象大小；原图预览通过短时签名 URL。删除原图时同步调用 COS 删除，失败保留 Asset 和持久化 `file_cleanups.PENDING`，用户可重试删除。已有导入任务的健康档案禁止删除。
