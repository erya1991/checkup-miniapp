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

阶段 00 已验收通过；阶段 01 工程骨架已实现，验收结果以 `docs/stages/01-foundation/RESULT.md` 为准。当前工程只包含健康检查和占位页，不包含业务闭环。

`docs/stages/01-foundation/`

## Stage 01 本地运行

| 工程 | 已实现入口 | 操作 |
| --- | --- | --- |
| PostgreSQL 17 | 根目录 `compose.yaml` | 复制 `.env.example` 为 `.env`，执行 `docker compose up -d postgres` |
| Backend | `GET /api/v1/health` | 按 `backend/README.md` 创建 Python 3.12 虚拟环境、安装依赖、执行迁移并启动 |
| Miniapp | 单一占位首页 | 在 `miniapp/` 执行 `pnpm install`、`pnpm typecheck`、`pnpm build:mp-weixin` |
| Admin Web | `/` 占位首页 | 在 `admin-web/` 执行 `pnpm install`、`pnpm dev`、`pnpm build` |

两个前端分别维护 `pnpm-lock.yaml`。真实 `.env` 不提交；后端使用 `DATABASE_URL`、`APP_ENV`、`LOG_LEVEL`。微信与 COS 配置尚未接入。当前数据库只有 Alembic 版本表，没有业务表。实际验收和未完成项见 Stage 01 RESULT。

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
