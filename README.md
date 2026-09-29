# 检查单小程序 Checkup Miniapp

面向个人及家庭成员的长期检验报告管理工具。

核心闭环：

`健康档案 → 上传报告 → OCR → AUTO/REVIEW → 人工确认 → 正式报告 → 指标历史 → 趋势 → 原始报告核对`

> 本产品用于检验报告整理、归档与趋势查看，不提供医疗诊断、疾病预测、AI 问诊或用药建议。

## 仓库结构

```text
checkup-miniapp/
├─ AGENTS.md
├─ README.md
├─ .env.example
├─ miniapp/                  # uni-app 微信小程序
├─ backend/                  # FastAPI + OCR Worker
├─ admin-web/                # Vue3 管理后台
├─ deploy/                   # Docker Compose / Nginx / scripts
├─ scripts/                  # 本地辅助脚本
└─ docs/
   ├─ 00-baseline/           # 长期产品/技术/研发基线
   ├─ 01-architecture/       # 专题技术设计
   ├─ stages/                # 分阶段计划、验收、结果
   └─ decisions/             # 长期架构决策记录
```

## 当前阶段

阶段 01、阶段 02 均已验收通过。阶段 02 已完成微信登录、健康档案、报告图片上传与私有 COS 的真实主流程验收；以 `docs/stages/02-profile-upload/RESULT.md` 为准。OCR 及正式报告尚未实现。

## Stage 02 本地运行

| 工程 | 已实现入口 | 操作 |
| --- | --- | --- |
| PostgreSQL 17 | 根目录 `compose.yaml` | 复制 `.env.example` 为 `.env`，执行 `docker compose up -d postgres` |
| Backend | `GET /api/v1/health` | 按 `backend/README.md` 创建 Python 3.12 虚拟环境、安装依赖、执行迁移并启动 |
| Miniapp | 登录、档案、上传和图片确认页 | 在 `miniapp/` 执行 `pnpm install`、`pnpm typecheck`、`pnpm build:mp-weixin`；将 `dist/build/mp-weixin` 导入微信开发者工具 |
| Admin Web | `/` 占位首页 | 在 `admin-web/` 执行 `pnpm install`、`pnpm dev`、`pnpm build` |

两个前端分别维护 `pnpm-lock.yaml`。真实 `.env` 不提交。后端运行前需将 `.env.example` 复制为 `.env`，设置 `DATABASE_URL`、至少 32 字符随机 `JWT_SECRET`、`WECHAT_APP_ID`、`WECHAT_APP_SECRET`、`COS_SECRET_ID`、`COS_SECRET_KEY`、`COS_BUCKET`、`COS_REGION`。执行 `docker compose up -d postgres`，在 `backend/` 执行 `.venv/Scripts/alembic.exe upgrade head` 和 `.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`。后端通过微信服务端 code 交换用户身份，签发自己的 Token；COS 永久密钥只在服务端使用。

微信开发者工具运行时，在 `miniapp/` 设置 `VITE_API_BASE_URL=https://<你的 API 域名>/api/v1` 并构建；开发者工具使用真实 AppID。微信公众平台应配置 HTTPS API 为 request 合法域名，COS 的 `https://<Bucket>.cos.<Region>.myqcloud.com` 为 request、uploadFile、downloadFile 合法域名，并按腾讯 COS 小程序接入要求配置白名单。COS Bucket 必须是私有读写。`miniapp/src/manifest.json` 保持 URL 合法域名检查开启。Stage 02 的真实验收结果见 `docs/stages/02-profile-upload/RESULT.md`。

Stage 02 自动验证命令：`backend/.venv/Scripts/python.exe -m pytest -q`、`backend/.venv/Scripts/ruff.exe check . --no-cache`；`miniapp/pnpm typecheck`、`miniapp/pnpm build:mp-weixin`；`admin-web/pnpm typecheck`、`admin-web/pnpm build`。已用 PostgreSQL 17 验证既有库和干净临时库迁移到 `0002_profile_upload`。当前新增四张核心表、上传授权表和文件清理记录表；不包含 OCR 表。

## Codex 使用方式

每个新 Codex 会话不需要粘贴全部历史需求。先要求 Codex：

1. 读取根目录 `AGENTS.md`；
2. 读取当前阶段 `PLAN.md` 与 `ACCEPTANCE.md`；
3. 按 `AGENTS.md` 指引按需读取 baseline / architecture；
4. 不扩大当前阶段范围；
5. 完成后执行验收并更新 `RESULT.md`。

推荐阶段 Prompt：

```text
当前开始执行研发阶段 XX。
请先读取根目录 AGENTS.md，然后读取当前阶段 PLAN.md 和 ACCEPTANCE.md，
并按 AGENTS.md 指引读取必要的 baseline / architecture 文档。
严格限制在 PLAN.md 范围内实施，不提前开发后续阶段能力。
完成后运行 ACCEPTANCE.md 要求的自动测试和手工检查，
并更新当前阶段 RESULT.md，记录完成项、测试结果、设计偏差、已知问题和下一阶段注意事项。
```

## 重要说明

现有 OCR PoC / Regression 建议继续保留在独立 `checkup-ocr-poc` 仓库。正式产品仓库只接入已验证的 OCR Pipeline 能力。
