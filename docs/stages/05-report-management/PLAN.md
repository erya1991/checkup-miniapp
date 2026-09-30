# Stage 05｜正式报告管理

**状态：READY\_FOR\_IMPLEMENTATION**

## 1\. 阶段目标

Stage 05 承接已经验收通过的 Stage 04。

Stage 04 已正式建立并验收通过：

```

ReportAsset
→ OcrTask
→ OcrResultItem
→ ConfirmationItem
→ commit
→ LabReport
→ LabResult
```

其中：

```

ReportIngestion / ReportAsset / OcrTask / OcrResultItem / ConfirmationItem
= 导入、OCR、确认与来源追溯域

LabReport / LabResult
= 正式健康数据域
```

Stage 05 的职责是：

> 对已经 commit 的正式检验报告提供完整、可信、安全的用户管理能力。

本阶段结束时必须形成：

```

选择 HealthProfile
→ 查看正式报告列表
→ 查看正式报告详情
→ 查看原始报告
→ 整份报告迁移 HealthProfile
→ 安全删除正式报告及其完整来源数据
```

Stage 05 不重新解释 OCR 数据，不修改正式检验结果，也不提前建设指标历史和趋势。

* * *

# 2\. 必读基线

实施前必须按 `AGENTS.md` 顺序读取：

1.  根目录 `AGENTS.md`
    
2.  `docs/00-baseline/PRODUCT_BASELINE.md`
    
3.  `docs/00-baseline/TECH_BASELINE.md`
    
4.  `docs/00-baseline/DEVELOPMENT_RULES.md`
    
5.  本目录 `PLAN.md`
    
6.  本目录 `ACCEPTANCE.md`
    
7.  `docs/stages/04-confirmation-report/RESULT.md`
    
8.  本阶段涉及正式数据、文件和 API，继续读取：
    
    *   `docs/01-architecture/DATA_MODEL.md`
        
    *   `docs/01-architecture/API_CONVENTIONS.md`
        
    *   `docs/01-architecture/SYSTEM_ARCHITECTURE.md`
        
    *   `docs/decisions/D-0003-ingestion-confirmation-report.md`
        

同时必须检查当前真实代码中的：

```

LabReport
LabResult
ConfirmationItem
OcrResultItem
OcrTask
ReportIngestion
ReportAsset
FileCleanup
HealthProfile

现有私有 COS preview
现有 ingestion/task 列表
Stage 04 commit 成功页
现有 PostgreSQL migration
```

不得根据旧对话中的代码假设直接实施。

* * *

# 3\. Stage 04 当前真实基础

截至 Stage 05 启动时，`main` 已包含 Stage 04 最终实现。

Stage 04 已确认：

*   `LabReport.source_ingestion_id` 唯一；
    
*   `LabResult.source_confirmation_item_id` 唯一；
    
*   commit 单事务生成 `LabReport / LabResult`；
    
*   `ReportIngestion.CONFIRMED` 表示正式保存完成；
    
*   commit 后 Confirmation 工作区被冻结；
    
*   正式报告检验日期来自 `examination_date`，不是上传时间；
    
*   `LabResult` 已保存正式指标名、StandardMetric、结果文本、数值、单位、参考范围、abnormal、data\_source；
    
*   正式结果可追溯到 Confirmation / OCR / 原图；
    
*   原图使用私有 COS；
    
*   原图预览使用后端鉴权后签发 300 秒短时 URL；
    
*   `FileCleanup` 当前只支持单 object 的删除失败记录；
    
*   OCR artifact 实际保存于：
    

```

users/{user_id}/ingestions/{ingestion_id}/ocr/
```

*   原始报告保存于：
    

```

users/{user_id}/ingestions/{ingestion_id}/original/
```

Stage 04 已明确：

```

Stage 05 尚未实现
```

因此本阶段不能假定已有正式报告 API 或正式报告页面。

* * *

# 4\. Stage 05 一句话职责

> Stage 05 负责 commit 后正式检验报告的浏览、原图追溯、整份档案迁移与完整删除。

本阶段操作对象是：

```

LabReport
+
LabResult
```

而不是重新使用：

```

OcrTask
OcrResultItem
ConfirmationItem
```

作为用户正式报告。

* * *

# 5\. 正式报告与识别任务必须继续分离

正式报告：

```

LabReport
→ LabResult
```

用于：

*   报告列表；
    
*   报告详情；
    
*   Stage 06 指标历史；
    
*   Stage 06 趋势。
    

识别任务：

```

ReportIngestion
→ OcrTask
→ ConfirmationItem
```

用于：

*   上传；
    
*   OCR；
    
*   OCR\_FAILED；
    
*   PENDING\_CONFIRMATION；
    
*   尚未完成的确认工作。
    

不得把：

```

PENDING_CONFIRMATION
OCR_FAILED
READY
```

等 ingestion 显示为正式报告。

也不得通过“识别任务记录”替代正式报告列表。

* * *

# 6\. 正式报告列表

## 6.1 数据范围

正式报告列表必须按当前 HealthProfile 查询。

API 必须显式传入：

```

health_profile_id
```

并先验证：

```

HealthProfile.id = health_profile_id
AND
HealthProfile.user_id = current_user.id
AND
HealthProfile.status = ACTIVE
```

之后只查询：

```

LabReport.user_id = current_user.id
AND
LabReport.health_profile_id = health_profile_id
```

不得跨 HealthProfile 混合展示。

不得从：

```

ReportIngestion
OcrTask
ConfirmationItem
```

补充“尚未正式保存”的记录。

* * *

## 6.2 默认排序

统一使用：

```

examination_date DESC
→ examination_time DESC，NULL 放后
→ created_at DESC
→ id DESC
```

主时间必须是检验时间。

不得使用：

*   上传时间；
    
*   OCR 时间；
    
*   commit 时间；
    
*   ingestion 创建时间
    

代替正式报告排序。

* * *

## 6.3 分页

Stage 05 必须实现服务端分页。

建议：

```

page >= 1
page_size 默认 20
page_size 最大 100
```

返回至少：

```

{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "has_more": false
}
```

小程序采用“加载更多”即可。

不建设复杂分页组件。

* * *

## 6.4 卡片展示

每张正式报告卡片至少展示：

*   检验日期；
    
*   检验时间，有则展示；
    
*   医院，有则展示；
    
*   报告分类，有则展示；
    
*   检验项目数量；
    
*   abnormal 有明确异常标记的项目数量；
    
*   报告编号可作为次要信息，有则展示。
    

异常数量只统计已经持久化的 `LabResult.abnormal`。

建议：

```

abnormal IS NOT NULL
AND abnormal != ''
AND abnormal != 'NORMAL'
```

页面文案使用：

```

3 项有异常标记
```

不要自行写成：

```

3 项异常
```

因为 Stage 05 不重新进行医学判断。

* * *

## 6.5 本阶段不做复杂筛选

Stage 05 P0 不建设：

*   医院筛选；
    
*   日期区间筛选；
    
*   报告分类筛选；
    
*   报告编号搜索；
    
*   全文搜索。
    

当前 HealthProfile 是本阶段唯一必须的业务过滤条件。

后续确有真实使用需求再增加。

* * *

# 7\. 正式报告详情

## 7.1 报告级信息

详情至少展示：

*   所属健康档案；
    
*   医院；
    
*   检验日期；
    
*   检验时间；
    
*   报告分类；
    
*   报告编号；
    
*   检验项目数量。
    

详情必须同时提供：

```

查看原始报告
迁移到其他档案
删除报告
```

不提供：

```

编辑报告
编辑检验结果
```

* * *

## 7.2 LabResult 顺序

结果按照：

```

sequence_no ASC
```

展示。

不得按 StandardMetric、名称或 abnormal 重新排序，从而破坏报告原有顺序。

* * *

## 7.3 正式指标名称

主展示名称使用：

```

LabResult.metric_name
```

它表示本次正式报告中用户最终确认后的项目名称。

如果：

```

standard_metric_id != NULL
```

则可以辅助展示：

```

标准指标：丙氨酸氨基转移酶（ALT）
```

StandardMetric 仅作为跨报告统一身份。

不得用 StandardMetric 名称覆盖本次报告正式 `metric_name`。

* * *

## 7.4 KEEP\_ORIGINAL\_NAME 与未关联指标

普通用户不展示：

```

KEEP_ORIGINAL_NAME
```

这种内部工程状态。

对于：

```

standard_metric_id = NULL
```

统一允许轻量展示：

```

未关联标准指标
```

该结果仍然属于本份正式报告，可以正常查看。

Stage 06 不得把这些结果直接纳入 StandardMetric 趋势聚合。

* * *

## 7.5 OCR\_AUTO / OCR\_CORRECTED / MANUAL

这些字段继续保留在正式数据中，但 Stage 05 普通详情不要求逐项展示。

当前 Stage 04 中 `OCR_CORRECTED / has_manual_correction` 的语义比“实际人工修改数值”更宽。

因此 Stage 05 不直接向用户展示：

```

该指标已人工修改
```

或：

```

本报告 X 项经过人工校正
```

避免产生不准确表达。

Stage 05 不因此重新修改 Stage 04 正式数据。

* * *

## 7.6 abnormal 展示

Stage 05 只展示：

```

LabResult.abnormal
```

不得根据：

```

result_numeric
reference_low
reference_high
```

重新计算 abnormal。

建议：

```

HIGH → ↑
LOW  → ↓
NORMAL → 不强调
NULL / 空 → 不显示判断
其它非空明确值 → 轻量显示“异常标记”
```

具体 OCR 已验证枚举按真实数据适配，但不得自行增加医学判定逻辑。

尤其：

```

abnormal = NULL
```

不代表“正常”。

* * *

## 7.7 非数值结果

正式详情始终使用：

```

result_text
```

作为用户主展示值。

例如：

```

阴性
阳性
未见异常
<0.5
1 至 3（复查）
```

都必须正常展示。

`result_numeric` 主要服务后续 Stage 06，不要求在 Stage 05 单独展示。

* * *

# 8\. 正式报告不可编辑

Stage 04 commit 后：

```

LabReport / LabResult
```

视为正式快照。

Stage 05 不新增：

```

PATCH /reports/{id}
PATCH /reports/{id}/results/{id}
```

也不允许从报告详情修改：

*   指标名称；
    
*   结果；
    
*   单位；
    
*   参考范围；
    
*   abnormal；
    
*   StandardMetric；
    
*   医院；
    
*   检验时间等正式内容。
    

Stage 05 唯一允许改变正式报告归属的操作是：

```

整份报告迁移 HealthProfile
```

如果正式数据本身错误，MVP 采用：

```

删除错误报告
→ 重新录入
```

而不是维护正式报告二次编辑历史。

* * *

# 9\. 原始报告查看

## 9.1 来源链

正式报告原图必须通过：

```

LabReport.source_ingestion_id
→ ReportIngestion
→ ReportAsset
→ Private COS
```

追溯。

不得在 `LabReport` 冗余复制 COS URL。

* * *

## 9.2 API

建议：

```

GET /api/v1/reports/{report_id}/assets

GET /api/v1/reports/{report_id}/assets/{asset_id}/preview
```

资产列表只返回必要元数据：

*   asset id；
    
*   page\_no；
    
*   mime\_type；
    
*   file\_size。
    

不得直接返回：

```

cos_object_key
永久 URL
```

preview API 继续复用当前：

```

preview_url()
```

生成短时私有 COS URL。

当前 300 秒有效期可继续使用。

* * *

## 9.3 多页原图

按照：

```

page_no ASC
```

展示。

小程序原始报告页应支持：

*   多页；
    
*   页面顺序正确；
    
*   点击放大；
    
*   `uni.previewImage` 或当前适合的小程序能力；
    
*   单页预览失败可单独重试。
    

Stage 05 不建设：

*   PDF 阅读器；
    
*   OCR bbox 高亮；
    
*   OCR 结果覆盖层；
    
*   图片标注工具。
    

* * *

## 9.4 原图异常

如果 ReportAsset 不存在：

```

REPORT_ASSET_NOT_FOUND
```

如果 COS 临时读取/签名失败：

使用稳定文件访问错误码。

原图读取失败不能导致正式报告详情本身无法查看。

页面显示：

```

原始报告暂时无法加载，请重试。
```

* * *

# 10\. 正式报告所属档案迁移

## 10.1 迁移粒度

只允许：

```

整份 LabReport
```

迁移。

禁止：

```

单条 LabResult 迁移
部分指标迁移
```

* * *

## 10.2 目标档案

目标 HealthProfile 必须满足：

```

HealthProfile.user_id = current_user.id
AND
HealthProfile.status = ACTIVE
```

绝对禁止跨用户迁移。

不得修改：

```

LabReport.user_id
ReportIngestion.user_id
```

* * *

## 10.3 单事务更新的数据

迁移时必须在同一个数据库事务中更新：

```

LabReport.health_profile_id
```

该报告全部：

```

LabResult.health_profile_id
```

以及来源：

```

ReportIngestion.health_profile_id
```

三处必须最终完全一致。

* * *

## 10.4 不修改的数据

迁移不修改：

```

ConfirmationItem
OcrResultItem
OcrTask
ReportAsset
```

因为这些实体通过 `ReportIngestion` 或来源外键保持追溯。

也不修改：

*   正式结果值；
    
*   metric\_name；
    
*   StandardMetric；
    
*   examination\_date/time；
    
*   report\_no；
    
*   hospital\_name；
    
*   source\_ingestion\_id；
    
*   source\_confirmation\_item\_id；
    
*   COS object key。
    

* * *

## 10.5 为什么 ReportIngestion 必须一起迁移

不得出现：

```

LabReport → 父亲

source ReportIngestion → 本人
```

这种来源语义冲突。

因此迁移正式报告时，来源 ingestion 的 health profile 必须一起迁移。

* * *

# 11\. 迁移事务与锁

迁移建议流程：

```

SELECT LabReport FOR UPDATE
↓
验证 report 属于 current User
↓
验证 target HealthProfile 属于 current User
↓
锁 target HealthProfile
↓
目标档案执行疑似重复检查
↓
更新 ReportIngestion.health_profile_id
↓
更新 LabReport.health_profile_id
↓
更新该 report 全部 LabResult.health_profile_id
↓
COMMIT
```

其中目标 HealthProfile 锁应与 Stage 04 commit 的 profile 锁语义保持一致。

目标：

```

commit 到目标档案
+
已有报告迁移到目标档案
```

在重复检测阶段可以正确串行化。

任一步失败：

```

全部 rollback
```

禁止出现半迁移。

* * *

# 12\. 迁移后的疑似重复检测

报告迁入目标 HealthProfile 后可能与目标档案已有报告重复，因此迁移必须重新进行疑似重复检查。

使用与 Stage 04 同样的产品原则：

```

疑似重复
→ 提示
→ 不自动覆盖
→ 不禁止用户继续
```

Stage 05 建议基于正式报告重新实现/抽取可复用的 duplicate 判断：

输入：

```

当前正式 LabReport
+
当前正式 LabResult 集合
+
target_health_profile_id
```

比较：

```

target HealthProfile
中的其它正式 LabReport / LabResult
```

必须排除当前正在迁移的 report。

至少继续支持 Stage 04 已有：

*   非空 report\_no 强标识；
    
*   日期 + 医院 + 指标集合高度重合。
    

不得通过读取 Confirmation 工作区重新构建正式报告。

* * *

## 12.1 重复 acknowledgement

发生疑似重复时继续返回：

```

DUPLICATE_CONFIRM_REQUIRED
```

并提供：

```

candidates
acknowledgement
```

acknowledgement 必须绑定至少：

*   report\_id；
    
*   目标 health\_profile\_id；
    
*   当前正式报告核心字段；
    
*   当前正式 LabResult 身份集合；
    
*   当前 duplicate candidate 集合。
    

如果：

```

目标 HealthProfile 改变
```

旧 acknowledgement 必须失效。

* * *

## 12.2 同档案迁移

如果：

```

target_health_profile_id
==
report.health_profile_id
```

视为安全 no-op。

不得重新制造报告。

不得修改数据。

可直接返回当前正式报告。

* * *

# 13\. 正式报告删除原则

正式报告删除是隐私删除，不是仅仅从列表隐藏。

用户明确删除报告时，应删除这次报告对应的完整健康数据链。

不得为了所谓审计永久保留用户明确要求删除的健康数据。

* * *

# 14\. 删除数据库范围

根据：

```

LabReport.source_ingestion_id
```

确定唯一 ingestion。

同一数据库事务内删除：

```

LabResult
LabReport

ConfirmationItem

OcrResultItem
OcrTask

ReportAsset
UploadAuthorization

ReportIngestion
```

其中：

*   删除全部 OCR runs；
    
*   删除全部 OCR Result；
    
*   删除 REMOVED Confirmation；
    
*   删除正式结果；
    
*   删除导入记录；
    
*   删除原图数据库索引。
    

不得保留医疗全文作为“审计历史”。

StandardMetric 等公共主数据不得删除。

* * *

# 15\. 删除采用硬删除

Stage 05 正式报告不增加：

```

deleted_at
is_deleted
RECYCLE_BIN
```

不建设回收站。

删除正式报告后：

```

LabReport 不存在
LabResult 不存在
```

因此未来 Stage 06：

```

报告历史
指标历史
趋势
```

自然不再查询到这些数据。

这是本阶段期望行为。

* * *

# 16\. COS 与数据库删除一致性

## 16.1 清理目标

正式报告删除必须清理整个 ingestion COS prefix：

```

users/{user_id}/ingestions/{ingestion_id}/
```

而不是只根据当前 ReportAsset 删除几张图片。

这样可以同时覆盖：

```

original/
ocr/
manifest
retry / evidence artifacts
可能存在的 ingestion 范围孤儿对象
```

* * *

## 16.2 删除事务第一阶段

在删除医疗数据库数据的同一个数据库事务中，先登记：

```

FileCleanup
```

清理目标：

```

target_type = PREFIX
cos_object_key = users/{user_id}/ingestions/{ingestion_id}/
status = PENDING
```

这里保留现有 `cos_object_key` 列名，以减少不必要 migration。

对于 `PREFIX` 类型，它存储 COS prefix。

只有：

```

FileCleanup PENDING
+
完整 DB 删除
```

同时成功时，数据库事务才允许 commit。

如果 FileCleanup 本身登记失败：

```

整个删除事务 rollback
正式报告继续存在
```

* * *

## 16.3 数据库 commit 后

数据库删除成功后：

```

报告列表立即消失
报告详情立即不可访问
Stage 06 数据立即自然消失
系统不再能为原 ReportAsset 签发新的 preview URL
```

随后执行一次即时 COS cleanup 尝试。

成功：

```

FileCleanup.status = DONE
```

失败：

```

FileCleanup.status 保持 PENDING
```

正式报告删除仍然视为用户操作成功。

COS 临时故障不能把已经完成的数据库隐私删除重新恢复。

* * *

## 16.4 DELETE API 返回

如果数据库事务成功：

```

DELETE /reports/{id}
→ 204
```

即使提交后的即时 COS 删除失败，也仍返回删除成功。

因为：

*   正式健康数据已经删除；
    
*   FileCleanup 已持久化；
    
*   后续会继续重试。
    

不得在数据库已删除后返回：

```

502 COS_DELETE_FAILED
```

使用户误以为报告仍存在。

* * *

# 17\. FileCleanup 扩展

当前 `FileCleanup` 已有：

```

cos_object_key
status
```

Stage 05 只增加真实需要的字段：

```

target_type
```

允许：

```

OBJECT
PREFIX
```

现有历史记录 migration 后统一为：

```

OBJECT
```

不因为“未来可能需要”增加：

*   report\_id；
    
*   ingestion\_id；
    
*   user\_id；
    
*   retry\_count；
    
*   last\_error\_message；
    
*   deleted\_at；
    
*   复杂任务时间字段。
    

* * *

# 18\. FileCleanup 重试消费者

Stage 05 必须真正具备后续重试能力。

不能只：

```

创建 PENDING
然后永远无人处理
```

实现一个轻量、幂等的 FileCleanup processor。

要求：

```

OBJECT
→ delete_object

PREFIX
→ 按 Prefix 分页列出对象
→ 批量/逐个删除
→ 直到 prefix 下为空
```

删除对象已经不存在时视为成功。

成功：

```

DONE
```

失败：

```

保持 PENDING
```

不得记录完整医疗数据。

Stage 05 可以在同一 backend codebase 增加轻量独立 cleanup worker/consumer 进程。

不引入：

*   Redis；
    
*   Celery；
    
*   RabbitMQ；
    
*   Kafka；
    
*   新数据库；
    
*   微服务。
    

如果部署配置因此新增一个 backend cleanup worker 进程，应同步更新必要技术说明，使文档与真实运行方式一致。

* * *

# 19\. 报告 API 范围

Stage 05 建议新增独立 report router/service。

至少：

```

GET /api/v1/reports
GET /api/v1/reports/{report_id}

GET /api/v1/reports/{report_id}/assets
GET /api/v1/reports/{report_id}/assets/{asset_id}/preview

POST /api/v1/reports/{report_id}/migrate

DELETE /api/v1/reports/{report_id}
```

列表：

```

GET /reports
?health_profile_id=
&page=
&page_size=
```

迁移 body：

```

{
  "health_profile_id": "...",
  "duplicate_acknowledgement": null
}
```

不增加正式数据编辑 API。

* * *

# 20\. report ownership helper

Stage 05 应形成统一：

```

report_for(...)
```

或等价所有权入口。

必须验证：

```

LabReport.user_id == current_user.id
```

并保证：

```

LabReport.health_profile_id
```

对应 HealthProfile 也属于 current User。

所有以下操作都必须经过统一 ownership 校验：

*   详情；
    
*   原图；
    
*   preview；
    
*   迁移；
    
*   删除。
    

不得只在前端校验。

* * *

# 21\. 小程序页面

Stage 05 最小新增：

```

pages/reports/index
pages/report-detail/index
pages/report-assets/index
```

分别负责：

```

正式报告列表
正式报告详情
原始报告
```

迁移和删除使用详情页弹窗完成，不建立独立页面。

本阶段优先业务闭环。

不投入大量时间进行视觉重构。

* * *

# 22\. 正式报告列表页

进入页面时读取：

```

current default HealthProfile
```

然后请求：

```

/reports?health_profile_id=...
```

必须处理：

*   loading；
    
*   empty；
    
*   error；
    
*   success；
    
*   load more；
    
*   切换健康档案后重新加载。
    

空状态可以提示：

```

暂无正式检验报告
```

并提供：

```

上传报告
```

入口。

* * *

# 23\. 正式报告详情页

详情页至少展示：

```

报告基本信息
+
正式 LabResult 列表
+
查看原始报告
+
迁移报告
+
删除报告
```

所有数据来自正式 report API。

不得为了展示方便继续调用：

```

/ingestions/{id}/confirmation
```

读取用户正式报告内容。

* * *

# 24\. 原始报告页

进入：

```

GET /reports/{id}/assets
```

按需：

```

GET /reports/{id}/assets/{asset_id}/preview
```

获取短时 URL。

允许多页。

原图 preview URL 不保存到长期 Store。

页面退出后不需要持久化。

* * *

# 25\. 迁移交互

详情页点击：

```

迁移到其他档案
```

展示当前用户 ACTIVE HealthProfile。

排除当前档案。

选择后进行确认：

```

将整份报告从「本人」迁移到「父亲」？
```

如果 API 返回：

```

DUPLICATE_CONFIRM_REQUIRED
```

展示目标档案中疑似重复报告基本信息。

允许：

```

取消
仍然迁移
```

成功后：

*   更新详情所属档案；
    
*   从原 HealthProfile 报告列表自然消失；
    
*   目标 HealthProfile 列表自然出现。
    

* * *

# 26\. 删除交互

详情页点击删除后必须出现危险操作确认。

明确说明：

> 删除后将同时删除该报告的检验结果、原始图片及识别数据，无法恢复。

用户明确确认后调用：

```

DELETE /reports/{id}
```

成功：

```

返回正式报告列表
刷新列表
```

不得保留已经删除报告的本地缓存。

* * *

# 27\. 首页与现有任务列表收口

当前首页真实代码可能把：

```

CONFIRMED ingestion
```

继续识别为当前 draft。

Stage 05 必须修正。

首页“当前导入任务”只考虑：

```

UPLOADING
READY
QUEUED
PROCESSING
OCR_FAILED
PENDING_CONFIRMATION
```

不得使用 `CONFIRMED` 作为继续上传/识别任务。

首页增加：

```

检验报告
```

正式入口。

继续保留：

```

识别任务记录
```

但识别任务记录默认不再展示已经 `CONFIRMED` 的任务作为正式报告入口。

正式报告统一从：

```

检验报告
```

进入。

* * *

# 28\. Stage 04 commit 后闭环

Stage 04 confirmation 页面 commit 成功后已经获得：

```

report_id
```

Stage 05 应增加：

```

查看检验报告
```

按钮：

```

/pages/report-detail/index?id={report_id}
```

仍可保留：

```

完成
返回首页
```

等现有最小反馈。

不得重新触发 OCR 或查询 Confirmation 作为正式详情。

* * *

# 29\. 数据模型与 migration

Stage 05 不修改：

```

LabReport
LabResult
ConfirmationItem
ReportIngestion
ReportAsset
OcrTask
OcrResultItem
```

的业务字段结构。

当前模型已经足够支持正式报告管理。

Stage 05 只需要新增 migration：

```

0005_report_management
```

核心修改：

```

FileCleanup.target_type
```

默认：

```

OBJECT
```

允许：

```

OBJECT
PREFIX
```

已应用的：

```

0001
0002
0003
0004
```

不得重写。

* * *

# 30\. 不增加正式报告软删除字段

不得为了删除增加：

```

LabReport.deleted_at
LabReport.status
LabResult.deleted_at
```

Stage 05 删除采用硬删除。

原因：

*   用户明确请求隐私删除；
    
*   当前没有恢复站需求；
    
*   Stage 06 需要自然不再查询到删除数据；
    
*   避免所有未来正式查询都携带软删除过滤条件。
    

* * *

# 31\. 不增加冗余趋势字段

Stage 05 不新增：

```

Trend
MetricHistory
report_metric_summary
latest_result
```

等趋势相关表或字段。

Stage 06 仍然直接基于：

```

LabResult
```

查询。

* * *

# 32\. Stage 06 数据基础

Stage 05 必须确保：

迁移：

```

LabResult.health_profile_id
```

正确更新。

删除：

```

LabResult
```

真正删除。

这样 Stage 06 查询：

```

health_profile_id
+
standard_metric_id
+
examination_date/time
```

即可自然得到正确结果。

Stage 05 不实现 Stage 06 API。

* * *

# 33\. 并发与事务重点

必须覆盖：

```

迁移 vs 迁移
迁移 vs 删除
迁移 vs 目标 HealthProfile 新 commit
重复 DELETE
```

关键要求：

### 迁移

```

LabReport
LabResult
ReportIngestion
```

不能出现半迁移。

### 删除

数据库完整链路：

```

正式域
确认域
OCR 域
上传域
```

不能只删除一半。

### FileCleanup

清理失败不得恢复健康数据。

重试必须幂等。

* * *

# 34\. 日志

允许记录：

```

request_id
user_id
report_id
ingestion_id
cleanup_id
status
error_code
duration
```

不得记录：

*   完整检验结果；
    
*   OCR 全文；
    
*   医疗报告图片；
    
*   永久 COS URL；
    
*   Secret；
    
*   SQL 异常中可能包含的医疗绑定值。
    

FileCleanup 失败优先记录：

```

cleanup_id
target_type
error_code
```

避免把完整 object prefix 打入普通业务日志。

* * *

# 35\. 自动测试重点

后端至少覆盖：

*   未 commit ingestion 不进入 reports；
    
*   HealthProfile 报告列表隔离；
    
*   分页；
    
*   稳定排序；
    
*   正式详情；
    
*   LabResult 顺序；
    
*   StandardMetric 有/无；
    
*   非数值结果；
    
*   abnormal 不重新计算；
    
*   原图 ownership；
    
*   短时预览；
    
*   多页原图；
    
*   整份迁移；
    
*   三处 health\_profile 一致更新；
    
*   同档案 no-op；
    
*   迁移 duplicate；
    
*   duplicate acknowledgement 失效；
    
*   跨用户迁移拒绝；
    
*   删除完整 DB 链；
    
*   FileCleanup PREFIX 创建；
    
*   COS 即时成功；
    
*   COS 即时失败仍 204；
    
*   PENDING 后续重试；
    
*   prefix 幂等删除；
    
*   Stage 04 commit/confirmation 全回归。
    

* * *

# 36\. PostgreSQL 17 集成验证

Stage 05 新增真实 PostgreSQL 集成验证。

建议：

```

backend/tests/verify_postgres_report_management.py
```

至少验证：

```

0004 → 0005
```

真实升级。

以及：

```

空库
0001 → 0002 → 0003 → 0004 → 0005
```

完整升级。

并验证：

*   migration 默认值；
    
*   Stage 04 正式报告可直接进入 Stage 05；
    
*   迁移事务 rollback；
    
*   三处 profile 一致；
    
*   目标 profile 并发锁；
    
*   迁移 vs 迁移；
    
*   迁移 vs 删除；
    
*   删除事务 rollback；
    
*   删除后完整数据链为空；
    
*   FileCleanup PREFIX 留存；
    
*   Stage 04 唯一约束未破坏。
    

临时数据库必须使用唯一命名，并在验证后删除。

不得修改开发人员当前真实业务数据库作为集成测试数据库。

* * *

# 37\. 小程序自动验证

至少运行：

```

pnpm test
pnpm typecheck
pnpm build:mp-weixin
```

建议将可纯逻辑测试的内容抽出：

*   report list path；
    
*   pagination merge；
    
*   active ingestion 判断；
    
*   report route；
    
*   migration duplicate retry payload；
    
*   deletion success navigation。
    

不得只依赖手工点击。

* * *

# 38\. Admin Web

Stage 05 不建设管理后台正式报告管理。

但必须保证：

```

pnpm typecheck
pnpm build
```

继续通过。

不得因为 Stage 05 修改公共依赖破坏 Admin Web。

* * *

# 39\. Stage 05 明确不做

本阶段禁止提前实现：

## Stage 06

*   我的指标；
    
*   指标历史；
    
*   趋势折线图；
    
*   最新指标；
    
*   单位趋势分组；
    
*   关注指标；
    
*   MetricFavorite。
    

## Stage 07

*   StandardMetric 管理后台；
    
*   MetricAlias 管理；
    
*   OCR 问题管理后台；
    
*   用户正式健康数据后台修改。
    

## 其它

*   正式报告编辑；
    
*   正式结果编辑；
    
*   医疗诊断；
    
*   AI 健康建议；
    
*   医院筛选；
    
*   日期筛选；
    
*   报告全文搜索；
    
*   报告公开分享；
    
*   回收站；
    
*   OCR 算法调整；
    
*   AUTO / REVIEW 判定规则调整。
    

* * *

# 40\. Stage 05 Definition of Done

Stage 05 只有同时满足以下条件才能 PASS：

```

Stage 04 全部回归通过

+

正式报告列表只使用正式数据
+
按 HealthProfile 正确隔离
+
分页与检验时间排序正确

+

正式报告详情完整
+
非数值结果正确
+
abnormal 不重新医学推断
+
未关联 StandardMetric 正确展示
+
正式报告不可编辑

+

正式报告可追溯多页私有原图
+
只生成短时访问 URL

+

整份报告档案迁移成功
+
LabReport / LabResult / ReportIngestion 三处归属一致
+
跨用户迁移禁止
+
目标档案重新执行疑似重复检查
+
迁移事务和并发安全

+

正式报告完整硬删除
+
Confirmation / OCR / Asset / Ingestion 同时删除
+
原图和 OCR artifact 进入 prefix 清理
+
FileCleanup 与 DB 删除同事务登记
+
COS 清理失败不恢复健康数据
+
PENDING cleanup 可后续重试
+
cleanup 幂等

+

首页正式报告入口完成
+
Stage 04 commit 后可直接查看正式报告
+
识别任务与正式报告入口分离

+

跨用户列表/详情/原图/迁移/删除隔离通过

+

0004 → 0005 PostgreSQL 17 migration PASS
+
空库完整 migration PASS
+
事务/并发集成 PASS

+

Backend pytest PASS
+
Ruff PASS
+
Miniapp tests PASS
+
Miniapp typecheck PASS
+
Miniapp build PASS
+
Admin typecheck/build PASS

+

负责人真实微信小程序人工验收全部 PASS
+
RESULT.md 完整
+
Stage 06 / Stage 07 未提前实现
```

任一 P0 未通过：

```

Stage 05 = FAIL
```

工程自动验证全部通过但负责人真实微信人工验收尚未完成时：

```

Stage 05 仍不得标记 PASS
```