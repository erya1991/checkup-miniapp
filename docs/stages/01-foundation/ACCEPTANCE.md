# 阶段 01｜ACCEPTANCE｜工程骨架

> 本文在开发前冻结。Codex 不得为了快速完成而删除验收项。

## A01｜仓库结构

- [ ] `backend/`、`miniapp/`、`admin-web/`、`deploy/`、`docs/`、`scripts/` 均存在。
- [ ] 根目录 `AGENTS.md` 和 baseline 文档仍存在，未被脚手架覆盖。

## A02｜Python 环境

在 `backend/` 激活 `.venv` 后：

```powershell
python --version
```

- [ ] 为 Python 3.12.x；项目基线目标为 3.12.10。

## A03｜PostgreSQL Docker

执行：

```powershell
docker compose up -d postgres
docker compose ps
```

- [ ] PostgreSQL 容器为 running/healthy（如配置 healthcheck）。
- [ ] 数据保存在命名 volume，不随容器重建丢失。

## A04｜FastAPI 启动

启动后端后访问：

```text
GET /api/v1/health
```

- [ ] HTTP 200。
- [ ] 返回 `status=ok`。
- [ ] API 启动配置来自环境变量而不是硬编码 Secret。

## A05｜数据库连接

- [ ] Backend 可以使用 `.env` 的 DATABASE_URL 连接 PostgreSQL。
- [ ] Alembic 已初始化。
- [ ] `alembic upgrade head` 可在空数据库正常执行。

## A06｜Backend 自动测试

建议命令（若工程封装了等价脚本，以 RESULT 中实际命令为准）：

```powershell
pytest
ruff check .
```

- [ ] pytest PASS。
- [ ] health API 有自动测试。
- [ ] ruff 无阻塞错误。

## A07｜Miniapp 安装与构建

在 `miniapp/`：

```powershell
pnpm install
pnpm build:mp-weixin
```

或项目脚手架定义的等价命令。

- [ ] 使用 pnpm，存在 `pnpm-lock.yaml`。
- [ ] 不存在 package-lock.json / yarn.lock。
- [ ] 微信小程序构建成功。
- [ ] 构建产物可被微信开发者工具导入/预览到占位页面。

## A08｜Miniapp 范围控制

- [ ] 未提前实现真实登录。
- [ ] 未提前实现健康档案、上传、OCR。
- [ ] 如建立 Tab，只为工程导航骨架，不包含后续业务逻辑。

## A09｜Admin Web

在 `admin-web/`：

```powershell
pnpm install
pnpm build
```

- [ ] 使用 pnpm。
- [ ] Vue3 + Vite + TypeScript + Element Plus 正常构建。
- [ ] 本地 dev 可打开占位页面。
- [ ] 未提前实现标准指标/OCR 管理业务。

## A10｜配置安全

执行：

```powershell
git status
```

并人工检查：
- [ ] `.env` 未被 Git 跟踪。
- [ ] 无微信 AppSecret、COS SecretKey、生产数据库密码进入源码。
- [ ] `.env.example` 只含占位值。

## A11｜文档

- [ ] Backend / Miniapp / Admin 各自 README 写明启动/构建命令。
- [ ] 若实际脚手架目录或命令与 PLAN 不同，已记录在 RESULT。
- [ ] `docs/stages/01-foundation/RESULT.md` 已更新。

## A12｜总体验收

在一台全新打开的开发终端，可以按照 README：

```text
启动 PostgreSQL
→ 启动 FastAPI
→ health=200
→ 构建 Miniapp
→ 构建 Admin Web
```

- [ ] 全流程无依赖“某个开发者电脑上未记录的手工配置”。

## 阶段退出条件

A01 ～ A12 全部 PASS 后，阶段 01 状态才能设置为 PASS，并进入阶段 02｜登录、健康档案与报告上传。
