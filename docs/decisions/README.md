# Architecture / Product Decisions

只记录影响多个阶段、未来容易被重新争论的重要决定。

建议格式：

```markdown
# D-XXXX｜标题

日期：YYYY-MM-DD
状态：Accepted / Superseded

## 决定

## 原因

## 影响

## 何时重新评估
```

当前初始决策：
- D-0001：正式 MVP 使用 FastAPI 单体后端；
- D-0002：V1.0 OCR Worker 使用 PostgreSQL 持久化队列，不引入 Redis/Celery；
- D-0003：OCR/确认域与正式报告域分离；
- D-0004：正式产品仓库与 OCR PoC/Regression 仓库保持职责分离。
