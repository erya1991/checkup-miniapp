# DATA_MODEL｜核心数据模型基线

> 本文定义概念模型与关键约束，不等同于最终数据库字段清单。具体字段在对应研发阶段通过 migration 落地。

## 1. 关系概览

```text
User 1 ─ N HealthProfile
User 1 ─ N ReportIngestion
HealthProfile 1 ─ N ReportIngestion
ReportIngestion 1 ─ N ReportAsset
ReportIngestion 1 ─ N OcrTask
OcrTask 1 ─ N OcrResultItem
ReportIngestion 1 ─ N ConfirmationItem
ReportIngestion 0..1 ─ 1 LabReport
LabReport 1 ─ N LabResult
StandardMetric 1 ─ N MetricAlias
StandardMetric 1 ─ N LabResult
HealthProfile N ─ N StandardMetric (via MetricFavorite)
```

## 2. User

核心：内部 ID、微信身份映射、状态、默认健康档案、创建/登录时间。

V1.0 不强制真实姓名、身份证、手机号。

## 3. HealthProfile

核心：所属 user、展示名称、关系、可选性别/生日、状态。

所有业务访问必须先验证 `HealthProfile.user_id == current_user.id`。

## 4. ReportIngestion

代表一次临时导入生命周期。

关键属性：
- user；
- health profile；
- mode: OCR / MANUAL；
- status；
- 临时报告信息（医院、检验日期/时间、报告号、分类）；
- duplicate status；
- confirmed time。

状态建议：
`UPLOADING → READY → QUEUED → PROCESSING → PENDING_CONFIRMATION → CONFIRMED`

异常：`OCR_FAILED / CANCELLED`。

## 5. ReportAsset

属于 ingestion 的原始文件：object key、page_no、mime、size、checksum、upload_status。

原始资产不可因为 OCR retry 被替换。

## 6. OcrTask

一次 OCR run：run_no、status、pipeline_version、开始/结束时间、错误信息、artifact path、duration。

状态：`QUEUED / PROCESSING / SUCCEEDED / FAILED`。

Retry 新建 OcrTask，不覆盖历史 run。

## 7. OcrResultItem

不可变机器识别快照。

至少保留：raw metric/result/unit/reference、标准指标匹配、AUTO/REVIEW、来源图片/page/bbox、必要 evidence 摘要。

## 8. ConfirmationItem

用户编辑的确认工作区。

可来自 OCR，也可纯手工新增。

核心概念：
- 可编辑最终候选值；
- standard_metric_id 可为空；
- source_type: `OCR_AUTO / OCR_CORRECTED / MANUAL`；
- review_status: `PENDING / RESOLVED`；
- resolution: `ACCEPTED / CORRECTED / STANDARD_METRIC_SELECTED / KEEP_ORIGINAL_NAME / MANUAL_ADDED / REMOVED`。

## 9. LabReport

仅 commit 后创建。

包含正式报告级信息、health profile、source ingestion、检验日期/时间、医院、报告号、分类、是否存在人工校正等。

`source_ingestion_id` 应具备唯一性，确保重复 commit 不产生多份报告。

## 10. LabResult

正式趋势数据源。

至少表达：
- report / health profile；
- 原始指标名；
- standard metric（可空）；
- result_text；
- 可选 result_numeric / comparator / result_type；
- original / normalized unit；
- reference text / 可解析上下限；
- abnormal flag；
- data source；
- source confirmation item。

## 11. StandardMetric / MetricAlias

StandardMetric 负责跨报告身份统一，不保存单一全局参考范围。
MetricAlias 负责常见中文名、英文名、缩写、医院名称、OCR 变体映射。

## 12. MetricFavorite

唯一约束：`health_profile_id + standard_metric_id`。

## 13. Audit

至少可记录 OCR 后人工修改、手工新增、删除错误项、手选标准指标、报告迁移档案等关键变化。
