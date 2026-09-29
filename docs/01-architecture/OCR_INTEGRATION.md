# OCR_INTEGRATION｜OCR 正式接入边界

## 1. 目标

把已经通过 PoC/Regression 的 Python OCR Pipeline 接入正式产品，而不是在正式业务开发阶段重新设计 OCR 算法。

## 2. 产品与 OCR 的契约

OCR Pipeline 输入：
- 一份 ReportIngestion 对应的 1..N 原始报告图片；
- 明确页序。

OCR Pipeline 输出至少包含：
- 报告级候选信息；
- 结构化检验行；
- 标准指标匹配；
- FINAL_AUTO / FINAL_REVIEW；
- 结果/单位/参考范围解析；
- 来源 page / bbox（可得时）；
- pipeline version；
- 可持久化原始审计产物。

## 3. 禁止事项

- Worker 不直接生成 LabReport；
- OCR 结果不直接进入趋势；
- 人工修改不覆盖 OcrResultItem；
- Retry 不覆盖旧 run；
- 业务页面不根据 OCR confidence 自行跳过 REVIEW；
- 算法 threshold / Retry / Evidence 规则 V1.0 不建设在线后台配置。

## 4. Worker

V1.0：
- 一个独立 Python Worker；
- PostgreSQL 队列；
- concurrency=1；
- 任务领取必须原子；
- 失败保存 error_code/error_message；
- 服务重启后 QUEUED 任务不丢。

后续阶段需要额外设计 PROCESSING 超时/Worker 崩溃后的恢复策略，但不得通过“直接标记成功”处理。

## 5. OCR Artifact

长期审计建议保留在 COS：

```text
/users/{user_uuid}/ingestions/{ingestion_uuid}/ocr/run-001/
  raw_ocr.json
  layout.json
  rows.json
  matched.json
  final.json
```

实际产物名称可随 Pipeline 调整，但必须保留 pipeline version 和 artifact root。

## 6. Regression 边界

OCR 准确率和安全门槛继续在独立 PoC 仓库回归。
正式产品仓库只测试：任务可靠性、结果映射、确认初始化、失败/重试、权限、commit 准入等业务逻辑。
