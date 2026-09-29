# Backend（Stage 03）

提供健康检查、微信 code 登录、健康档案、COS 原图资产，以及 Stage 03 的 OCR 任务、持久化队列与独立 Worker。迁移 `0003_ocr` 增加 OcrTask / OcrResultItem 并扩展 ingestion 状态。识别成功只到 `PENDING_CONFIRMATION`，不生成正式健康数据。

在仓库根目录复制 `.env.example` 为不提交的 `.env`，设置 `POSTGRES_*` 与一致的 `DATABASE_URL`，以及至少 32 字符的 `JWT_SECRET`、微信 `WECHAT_APP_ID` / `WECHAT_APP_SECRET`、私有 COS 的 `COS_SECRET_ID` / `COS_SECRET_KEY` / `COS_BUCKET` / `COS_REGION`。先运行 `docker compose up -d postgres`。永久密钥不得进入 Git 或小程序。

PowerShell（在 `backend/`）：

```powershell
& 'C:\Users\65410\AppData\Local\Programs\Python\Python312\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev,ocr]'
py -3.12 -m venv .venv-paddle
.\.venv-paddle\Scripts\python.exe -m pip install -r ocr-paddle-requirements.txt
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

第一行解释器路径是本次开发机的实测位置；其它开发机请替换为自己的 Python 3.12.x 路径。访问 `http://127.0.0.1:8000/api/v1/health`。

另开终端执行 `.\.venv\Scripts\python.exe -m app.ocr_worker`。Worker 固定单任务执行；`.env` 的 `OCR_NORMAL_PYTHON` 与 `OCR_PADDLE_PYTHON` 分别指向这两套环境，`OCR_WORK_DIR` 指向未跟踪临时目录。`OCR_TASK_LEASE_SECONDS` 默认 1800 秒；J03 可设为 60 或 120 秒，重启 Worker 后对新 OCR 任务生效，heartbeat 续租间隔按 lease 缩短。PoC 运行源码与模型已随 `backend/ocr_runtime/` 固定，来源和哈希见其 README。Worker 从冻结的 manifest 按页序读取私有 COS 原图，并把所有输出放在每次 run/attempt 专用的私有 COS 前缀。成功后可通过 `GET /api/v1/ingestions/{id}/ocr` 读取汇总状态。

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe tests\verify_postgres_queue.py
```

配置读取仓库根目录 `.env` 或进程环境变量；`DATABASE_URL` 必填。常规 pytest mock 微信身份交换和 COS 服务端操作；独立的 PostgreSQL 队列脚本使用唯一命名临时数据库。COS 授权仅对一个随机 object key 开放 15 分钟 PutObject；登记时后端 HEAD 验证对象大小；原图预览通过短时签名 URL。删除原图时同步调用 COS 删除，失败保留 Asset 和持久化 `file_cleanups.PENDING`，用户可重试删除。已有导入任务的健康档案禁止删除。
