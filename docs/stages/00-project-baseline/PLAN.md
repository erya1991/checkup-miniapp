# 阶段 00｜项目规范、仓库结构、开发环境与 Codex 上下文体系

## 1. 阶段目标

在任何业务代码开发前，把项目长期上下文、目录、环境、阶段机制固化到 Git 仓库，让后续 Codex 会话不依赖历史聊天即可恢复正确的产品和技术边界。

## 2. 本阶段范围

### 仓库
- 固定顶层目录；
- 建立 `.gitignore` / `.gitattributes` / `.env.example`；
- 记录 Python/Node 版本基线。

### Codex 上下文
- 根目录 `AGENTS.md`；
- 产品、技术、研发、环境、术语 baseline；
- architecture 专题文档；
- decision 机制。

### 阶段机制
- 固定 PLAN / ACCEPTANCE / RESULT 三文档模式；
- 建立阶段模板；
- 写完整阶段 01 PLAN / ACCEPTANCE。

### 环境
- 明确必须安装软件；
- 提供环境检查命令/脚本；
- 明确哪些服务使用 Docker。

## 3. 本阶段明确不做

- 不写 FastAPI 业务代码；
- 不创建数据库表；
- 不初始化 uni-app 业务页面；
- 不接微信登录；
- 不接 COS；
- 不接 OCR；
- 不安装 Redis/Celery 等非 V1.0 技术。

## 4. 交付物

- `AGENTS.md`；
- baseline 文档；
- architecture 文档；
- stage 模板；
- 阶段 01 PLAN / ACCEPTANCE；
- 环境检查脚本；
- 仓库基础配置模板。

## 5. 完成条件

以 `ACCEPTANCE.md` 为准。
