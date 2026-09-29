# 阶段 01｜正式项目工程骨架

## 1. 阶段目标

建立三个可以独立启动/构建的工程骨架和最小数据库开发环境，为后续登录、健康档案、上传和 OCR 开发提供稳定基础。

本阶段完成后必须做到：
- FastAPI 可以启动并返回健康检查；
- PostgreSQL 17 可通过 Docker 启动；
- SQLAlchemy/Alembic 工程已建立并能连接数据库；
- uni-app Vue3 TypeScript 工程可以构建微信小程序；
- Admin Vue3/Vite/Element Plus 工程可以启动和构建；
- 配置、测试和文档机制正常。

**本阶段不开发任何真实业务闭环。**

## 2. 上游依赖

必须先通过阶段 00：
- 软件环境正确；
- AGENTS / baseline 已进入正式仓库；
- `.env` 本地配置方式明确。

## 3. Backend 范围

### 3.1 初始化

在 `backend/` 创建正式 Python 工程。

建议至少包含：

```text
backend/
├─ app/
│  ├─ main.py
│  ├─ api/
│  │  └─ v1/
│  ├─ core/
│  │  ├─ config.py
│  │  └─ logging.py
│  ├─ db/
│  │  ├─ base.py
│  │  └─ session.py
│  └─ models/
├─ migrations/
├─ tests/
├─ pyproject.toml
└─ README.md
```

可根据 FastAPI/SQLAlchemy 常规组织做小幅调整，但不得提前创建 HealthProfile/OCR 等业务模型。

### 3.2 最小依赖

至少包含：
- FastAPI；
- Uvicorn；
- Pydantic Settings；
- SQLAlchemy 2.x；
- psycopg；
- Alembic；
- pytest；
- httpx（API 测试）；
- ruff。

不要加入 OCR 大依赖；OCR 依赖阶段 03 再接。

### 3.3 配置

从环境变量读取：
- APP_ENV；
- DATABASE_URL；
- LOG_LEVEL 等。

禁止源码写死密码。

### 3.4 API

本阶段只实现：

`GET /api/v1/health`

返回应用健康信息，例如：

```json
{
  "status": "ok",
  "service": "checkup-api"
}
```

本阶段不实现微信登录、User、HealthProfile。

### 3.5 Database

- Docker Compose 启动 PostgreSQL 17；
- FastAPI 能建立连接；
- 初始化 Alembic；
- 建立可在空库执行的初始 migration 基础（允许无业务表）。

不要为了“测试数据库”提前创建正式业务表。

## 4. Miniapp 范围

在 `miniapp/` 初始化：
- uni-app；
- Vue 3；
- TypeScript；
- pnpm；
- 微信小程序构建目标。

阶段 01 只需要：
- 可运行基础首页占位；
- 三个 Tab 的骨架可以暂时只创建路由/占位页，或只创建最小导航结构，以确保后续路由基础可用；
- 基础 API base URL 配置入口。

不实现：
- 微信登录；
- 健康档案；
- 报告上传；
- OCR 页面；
- 正式视觉设计。

如果 uni-app 当前脚手架要求不同目录结构，以可正常构建微信小程序为优先，并在 RESULT 记录实际结构。

## 5. Admin Web 范围

在 `admin-web/` 初始化：
- Vue 3；
- Vite；
- TypeScript；
- Element Plus；
- Vue Router；
- pnpm。

只实现：
- 基础 Layout/占位首页；
- 路由可用；
- 能 dev/build。

不实现登录逻辑和业务菜单。

## 6. Deploy 范围

建立开发用 Docker Compose：
- PostgreSQL 17。

生产 Nginx 可保留目录/说明，但本阶段不要求完成生产配置。

Compose 数据库：
- 使用 volume 持久化；
- 密码从 `.env` 读取；
- 不写真实生产凭据。

## 7. 工程质量

Backend：
- 最少一个 health API 自动测试；
- ruff 可以执行；
- pytest 可以执行。

Frontend：
- 两个前端工程均有明确 `dev/build` 脚本；
- 使用 pnpm；
- 不产生第二种 lockfile。

## 8. 文档

- `backend/README.md` 补充本地启动方式；
- `miniapp/README.md` 补充构建微信小程序方式；
- `admin-web/README.md` 补充启动方式；
- 如果实际脚手架/命令与本 PLAN 不同，在 RESULT 记录差异。

## 9. 本阶段明确不做

- 微信登录；
- User / HealthProfile 表；
- COS；
- ReportIngestion；
- OCR Worker；
- 标准指标库；
- 管理后台业务 CRUD；
- Redis / Celery；
- 生产域名/HTTPS；
- UI 精细设计。

## 10. 完成条件

以 `ACCEPTANCE.md` 为唯一验收基线。全部 P0 通过后才进入阶段 02。
