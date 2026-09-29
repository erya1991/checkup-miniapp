# 文档索引

本目录保存项目长期上下文。设计目标是让新的 Codex 会话能够通过仓库恢复上下文，而不是依赖旧聊天记录。

## 00-baseline

长期稳定且跨阶段生效：
- `PRODUCT_BASELINE.md`：产品边界与关键业务规则；
- `TECH_BASELINE.md`：技术路线与系统边界；
- `DEVELOPMENT_RULES.md`：研发、测试、Git、配置规则；
- `ENVIRONMENT_SETUP.md`：本地软件与环境；
- `GLOSSARY.md`：统一术语。

## 01-architecture

当开发涉及相应主题时按需读取：
- 系统架构；
- 数据模型；
- API 约定；
- OCR 正式接入边界。

## stages

每阶段固定三份文档：
- `PLAN.md`：这一阶段做什么和不做什么；
- `ACCEPTANCE.md`：开发前冻结的验收标准；
- `RESULT.md`：实施后形成的项目事实记录。

## decisions

用于保存影响多个阶段的长期决策。不要把普通实现细节都写成决策记录。
