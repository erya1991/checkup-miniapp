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

Stage 08 用户明确确认删除后物理删除 HealthProfile，同一事务清理当前归属的正式报告/结果、Confirmation、全部OCR run/结果、Asset、UploadAuthorization、Ingestion和MetricFavorite。公共StandardMetric/MetricAlias不属于用户私有删除范围。历史status=DELETED空档案不自动批量清理。任一PROCESSING task使删除返回PROFILE_DELETE_BUSY并整体回滚，不强制取消OCR。

默认档案被删除时，按同用户剩余ACTIVE的created_at ASC、id ASC稳定替换，无剩余则NULL。用户侧生命周期写操作在业务行锁前取得按User ID区分的PostgreSQL事务advisory lock；整档案删除按task→ingestion行锁顺序与Worker协调，跨档案迁移与删除串行，仍以当前归属为准。

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

Stage 07：StandardMetric 增加可空 `category` 字符串；code 创建后只读；name/category 可维护；状态 ACTIVE/INACTIVE。PENDING_CONFIRMATION 的 ConfirmationItem 引用阻止停用；已 CONFIRMED 的引用不阻止停用。停用不隐藏已有正式历史、趋势或 Favorite。无参考范围、单位换算或复杂分类表。

MetricAlias 包含 id、standard_metric_id FK、原始 alias、normalized_alias、alias_type、status、created_at、updated_at。type 为 SYNONYM / ABBREVIATION / OCR_VARIANT / HOSPITAL_NAME，只作管理元数据；目标创建后只读，无物理删除。ACTIVE normalized_alias 全局唯一，PostgreSQL partial unique index 保护；采用统一 NFKC、前导星号、gamma、casefold、简单分隔符归一化，并双向检查 ACTIVE namespace 冲突。

Alias 只增强搜索与未来 Confirmation 首次初始化的 exact 预关联。优先可靠 OCR code，再 raw_metric 的 canonical name/code exact，再 Alias exact；歧义名称保守不关联。REVIEW 命中仍 PENDING；无可靠产品 code 映射的 FINAL_AUTO 不因 Alias 自动解决。旧 Confirmation、LabResult、OcrResultItem 不随主数据维护重算或回填。冻结 OCR matcher/Pipeline 不读取数据库 Alias。

## 12. MetricFavorite

唯一约束：`health_profile_id + standard_metric_id`。

整档案隐私删除时物理清除该档案全部关注，不迁入其它档案。单报告删除仍允许保留该档案的dormant Favorite，保持Stage06原语义。

## FileCleanup

Stage05支持OBJECT/PREFIX与PENDING/DONE；Stage08新增nullable TIMESTAMPTZ `not_before`及(status,not_before,created_at)索引。每个待删ingestion的`users/{user_id}/ingestions/{ingestion_id}/`完整PREFIX cleanup先在同一删除事务登记，覆盖原图、OCR产物、retry/evidence以及未登记孤儿对象。

无未来有效UploadAuthorization时not_before=NULL，立即可处理；有未来有效授权（包括consumed）时为最大expires_at+60秒。授权保存真实STS过期时间与本地15分钟的较晚值。worker只执行到期PENDING；失败保持PENDING，可重试，重复清理幂等。数据库删除提交后不因COS故障恢复健康数据；文件在凭据窗口结束后最终清除。既有NULL记录和Stage05单份报告即时清理语义保持。

## 13. Audit

至少可记录 OCR 后人工修改、手工新增、删除错误项、手选标准指标、报告迁移档案等关键变化。
