# 分阶段研发目录

固定模式：

```text
<stage>/
├─ PLAN.md
├─ ACCEPTANCE.md
└─ RESULT.md
```

- PLAN：开发前冻结；
- ACCEPTANCE：开发前冻结；
- RESULT：开发后由实施者/Codex 填写。

当前阶段顺序：

| 阶段 | 名称 | 核心目标 |
|---|---|---|
| 00 | project-baseline | 仓库、环境、长期上下文、验收机制 |
| 01 | foundation | 三端工程骨架 + FastAPI/PostgreSQL 基础 |
| 02 | profile-upload | 登录、健康档案、COS 报告上传 |
| 03 | ocr-integration | OCR Worker 正式接入 |
| 04 | confirmation-report | 人工确认、commit、正式报告 |
| 05 | report-management | 报告列表、详情、原图、迁移、删除 |
| 06 | metric-trend | 我的指标、历史、趋势、关注 |
| 07 | admin | 轻量管理后台 |
| 08 | profile-data-deletion | 健康档案隐私删除与数据生命周期闭环 |

阶段 02～08 的详细 PLAN/ACCEPTANCE 在进入相应阶段前生成，不提前固化过多实现细节。
