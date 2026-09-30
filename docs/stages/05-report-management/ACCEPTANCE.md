# Stage 05｜正式报告管理验收标准

> 本文是 Stage 05 的冻结验收基线。
> 
> Stage 05 只有所有 P0 项全部通过，且项目负责人完成真实微信小程序人工验收后，才能最终判定 PASS。

* * *

# A. 前序基线与范围

## A01｜Stage 04 已正式 PASS【P0】

确认当前仓库：

```

Stage 04 RESULT = PASS
```

并且正式存在：

```

ReportIngestion
ReportAsset
OcrTask
OcrResultItem
ConfirmationItem
LabReport
LabResult
```

*   PASS
    
*   FAIL
    

* * *

## A02｜Stage 04 已有正式报告无需重新 commit【P0】

Stage 04 已经生成的：

```

LabReport / LabResult
```

升级 Stage 05 后可以直接进入正式报告列表和详情。

不得：

```

重新 OCR
重新 Confirmation
重新 commit
```

*   PASS
    
*   FAIL
    

* * *

## A03｜正式域与 OCR/确认域继续分离【P0】

正式报告查询不得把：

```

ReportIngestion
OcrTask
OcrResultItem
ConfirmationItem
```

当成正式健康报告。

只有：

```

LabReport / LabResult
```

进入正式报告管理。

*   PASS
    
*   FAIL
    

* * *

# B. Migration 与数据模型

## B01｜新增 migration 不重写历史 migration【P0】

Stage 05 使用新的：

```

0005_report_management
```

或等价后继 migration。

不得修改：

```

0001
0002
0003
0004
```

已应用 migration。

*   PASS
    
*   FAIL
    

* * *

## B02｜FileCleanup 支持 OBJECT / PREFIX【P0】

Stage 05 增加：

```

target_type
```

至少支持：

```

OBJECT
PREFIX
```

*   PASS
    
*   FAIL
    

* * *

## B03｜历史 FileCleanup 默认保持 OBJECT【P0】

从 Stage 04 数据库升级后：

```

已有 FileCleanup.target_type = OBJECT
```

不得破坏现有单对象删除行为。

*   PASS
    
*   FAIL
    

* * *

## B04｜不为正式报告增加软删除字段【P0】

不得新增仅为 Stage 05 删除服务的：

```

LabReport.deleted_at
LabReport.is_deleted
LabResult.deleted_at
```

*   PASS
    
*   FAIL
    

* * *

## B05｜不为 Stage 06 提前新增趋势数据表【P0】

Stage 05 不新增：

```

Trend
MetricHistory
MetricFavorite
latest_result
```

等 Stage 06 数据结构。

*   PASS
    
*   FAIL
    

* * *

# C. 正式报告列表

## C01｜列表必须指定 HealthProfile【P0】

`GET /api/v1/reports` 必须按：

```

health_profile_id
```

查询。

*   PASS
    
*   FAIL
    

* * *

## C02｜HealthProfile 必须属于当前 User【P0】

使用他人：

```

health_profile_id
```

请求报告列表时不得返回任何对方报告信息。

*   PASS
    
*   FAIL
    

* * *

## C03｜只返回正式 LabReport【P0】

以下 ingestion 均不得进入正式列表：

```

UPLOADING
READY
QUEUED
PROCESSING
OCR_FAILED
PENDING_CONFIRMATION
```

*   PASS
    
*   FAIL
    

* * *

## C04｜不同 HealthProfile 不混合【P0】

同一用户：

```

本人
父亲
母亲
```

三个档案的正式报告必须完全隔离。

*   PASS
    
*   FAIL
    

* * *

## C05｜默认使用检验日期排序【P0】

排序优先：

```

examination_date DESC
```

不得使用上传/commit 时间作为主排序。

*   PASS
    
*   FAIL
    

* * *

## C06｜同日时间排序正确【P0】

同一天多份报告：

```

examination_time
```

较晚者优先。

无 examination\_time 的报告仍可正常排序。

*   PASS
    
*   FAIL
    

* * *

## C07｜稳定排序【P0】

日期和时间相同的报告必须有稳定次级排序，不得翻页后随机重复或漏项。

*   PASS
    
*   FAIL
    

* * *

## C08｜服务端分页【P0】

支持至少：

```

page
page_size
```

并返回：

```

total
has_more
```

或等价明确分页元数据。

*   PASS
    
*   FAIL
    

* * *

## C09｜page\_size 有上限【P0】

客户端不得通过超大 page\_size 一次读取全部长期历史。

*   PASS
    
*   FAIL
    

* * *

## C10｜列表项目数量正确【P0】

每张卡片的：

```

item_count
```

与实际 `LabResult` 数量一致。

*   PASS
    
*   FAIL
    

* * *

## C11｜异常标记数量只读正式 abnormal【P0】

列表异常数量只根据：

```

LabResult.abnormal
```

统计。

不得重新根据参考范围计算。

*   PASS
    
*   FAIL
    

* * *

# D. 正式报告详情

## D01｜只能查看当前用户正式报告【P0】

`GET /reports/{report_id}` 必须验证当前用户 ownership。

*   PASS
    
*   FAIL
    

* * *

## D02｜报告基本信息完整【P0】

至少返回：

```

health_profile
hospital_name
examination_date
examination_time
report_no
report_category
item_count
```

*   PASS
    
*   FAIL
    

* * *

## D03｜正式结果按 sequence\_no【P0】

LabResult 使用：

```

sequence_no ASC
```

展示。

*   PASS
    
*   FAIL
    

* * *

## D04｜metric\_name 为主名称【P0】

正式详情的指标主名称必须来自：

```

LabResult.metric_name
```

不得被 StandardMetric 名称覆盖。

*   PASS
    
*   FAIL
    

* * *

## D05｜StandardMetric 可辅助展示【P0】

有 `standard_metric_id` 时可以返回：

```

id
code
name
```

等必要信息。

*   PASS
    
*   FAIL
    

* * *

## D06｜standard\_metric\_id = NULL 可正常展示【P0】

未关联标准指标的正式 LabResult：

```

仍然必须正常展示
```

不得被过滤掉。

*   PASS
    
*   FAIL
    

* * *

## D07｜KEEP\_ORIGINAL\_NAME 不暴露工程枚举【P0】

普通用户界面不显示：

```

KEEP_ORIGINAL_NAME
```

可统一表达：

```

未关联标准指标
```

*   PASS
    
*   FAIL
    

* * *

## D08｜非数值结果正常展示【P0】

例如：

```

阴性
阳性
未见异常
```

必须完整返回和显示。

*   PASS
    
*   FAIL
    

* * *

## D09｜result\_text 为用户主展示值【P0】

不得要求：

```

result_numeric != NULL
```

才展示检验结果。

*   PASS
    
*   FAIL
    

* * *

## D10｜abnormal = NULL 不显示“正常”【P0】

缺少 abnormal 时不得自行推断：

```

正常
```

*   PASS
    
*   FAIL
    

* * *

## D11｜Stage 05 不重新计算 abnormal【P0】

报告详情不得根据：

```

result_numeric
reference_low
reference_high
```

进行新的医学判断。

*   PASS
    
*   FAIL
    

* * *

## D12｜普通详情不强制展示 data\_source【P0】

UI 不逐条显示：

```

OCR_AUTO
OCR_CORRECTED
MANUAL
```

内部数据可以保留。

*   PASS
    
*   FAIL
    

* * *

## D13｜正式结果不可编辑【P0】

不存在允许用户修改正式 LabResult 值的正式报告 API 或页面入口。

*   PASS
    
*   FAIL
    

* * *

# E. 原始报告追溯

## E01｜正式报告可找到 source ingestion【P0】

通过：

```

LabReport.source_ingestion_id
```

可追溯到原始 ingestion。

*   PASS
    
*   FAIL
    

* * *

## E02｜正式报告资产只属于 source ingestion【P0】

原图列表不得串入其它 ingestion 的 ReportAsset。

*   PASS
    
*   FAIL
    

* * *

## E03｜多页顺序正确【P0】

ReportAsset 按：

```

page_no ASC
```

返回。

*   PASS
    
*   FAIL
    

* * *

## E04｜原图列表不返回 cos\_object\_key【P0】

普通小程序 API 不暴露内部 COS object key。

*   PASS
    
*   FAIL
    

* * *

## E05｜预览使用短时 URL【P0】

preview API 继续使用后端鉴权后生成的私有 COS 临时地址。

不得生成永久公开 URL。

*   PASS
    
*   FAIL
    

* * *

## E06｜跨用户原图列表被拒绝【P0】

用户 A 不得读取用户 B 报告的 asset 元数据。

*   PASS
    
*   FAIL
    

* * *

## E07｜跨用户 preview 被拒绝【P0】

用户 A 不得通过猜测：

```

report_id
asset_id
```

获取用户 B 原图临时 URL。

*   PASS
    
*   FAIL
    

* * *

## E08｜单页预览失败不破坏正式报告详情【P0】

COS 预览暂时失败时：

```

正式报告详情仍可查看
```

*   PASS
    
*   FAIL
    

* * *

# F. 正式报告迁移

## F01｜迁移必须整份执行【P0】

不提供：

```

单条 LabResult 迁移
```

*   PASS
    
*   FAIL
    

* * *

## F02｜只能迁移到当前用户 ACTIVE HealthProfile【P0】

目标档案必须属于当前用户。

*   PASS
    
*   FAIL
    

* * *

## F03｜跨用户目标档案禁止【P0】

用户不得通过手工构造 ID 将报告迁入他人 HealthProfile。

*   PASS
    
*   FAIL
    

* * *

## F04｜LabReport profile 更新【P0】

成功迁移后：

```

LabReport.health_profile_id = target
```

*   PASS
    
*   FAIL
    

* * *

## F05｜全部 LabResult profile 更新【P0】

该报告所有：

```

LabResult.health_profile_id = target
```

*   PASS
    
*   FAIL
    

* * *

## F06｜ReportIngestion profile 更新【P0】

来源：

```

ReportIngestion.health_profile_id = target
```

*   PASS
    
*   FAIL
    

* * *

## F07｜三处 profile 始终一致【P0】

成功事务后：

```

LabReport.health_profile_id
==
all LabResult.health_profile_id
==
ReportIngestion.health_profile_id
```

*   PASS
    
*   FAIL
    

* * *

## F08｜正式值不因迁移改变【P0】

迁移前后：

*   metric\_name；
    
*   result\_text；
    
*   unit；
    
*   reference；
    
*   abnormal；
    
*   StandardMetric；
    
*   examination\_date/time
    

保持一致。

*   PASS
    
*   FAIL
    

* * *

## F09｜来源链不被重建【P0】

迁移不得重新：

```

OCR
初始化 Confirmation
commit
```

*   PASS
    
*   FAIL
    

* * *

## F10｜同档案迁移安全 no-op【P0】

迁移到当前档案不得产生错误副本或修改正式结果。

*   PASS
    
*   FAIL
    

* * *

# G. 迁移重复检测

## G01｜目标档案重新进行重复检测【P0】

不得沿用报告在源档案时的 duplicate 判断。

*   PASS
    
*   FAIL
    

* * *

## G02｜重复检测只比较目标档案【P0】

不得跨其它 HealthProfile 判断或泄露候选。

*   PASS
    
*   FAIL
    

* * *

## G03｜当前 report 从 duplicate candidates 排除【P0】

不得把正在迁移的报告自己识别为重复候选。

*   PASS
    
*   FAIL
    

* * *

## G04｜强报告编号规则继续有效【P0】

目标档案存在相同非空报告编号等 Stage 04 强规则时能提示。

*   PASS
    
*   FAIL
    

* * *

## G05｜日期 + 医院 + 指标集合规则继续有效【P0】

Stage 04 组合重复逻辑在迁移场景继续有效。

*   PASS
    
*   FAIL
    

* * *

## G06｜疑似重复只提示不禁止【P0】

返回：

```

DUPLICATE_CONFIRM_REQUIRED
```

后允许用户明确继续迁移。

*   PASS
    
*   FAIL
    

* * *

## G07｜取消重复迁移不修改任何数据【P0】

用户没有提交 acknowledgement 时：

```

三处 health_profile 均保持原值
```

*   PASS
    
*   FAIL
    

* * *

## G08｜旧 acknowledgement 对新目标失效【P0】

更换目标 HealthProfile 后旧 acknowledgement 不得继续生效。

*   PASS
    
*   FAIL
    

* * *

# H. 迁移事务与并发

## H01｜迁移单事务【P0】

三处 profile 更新只能：

```

全部成功
或
全部 rollback
```

*   PASS
    
*   FAIL
    

* * *

## H02｜迁移中途数据库异常完整回滚【P0】

人工注入数据库错误后不得出现半迁移。

*   PASS
    
*   FAIL
    

* * *

## H03｜并发迁移同一报告安全【P0】

两个独立 session 同时迁移同一 report，不得产生不一致状态。

*   PASS
    
*   FAIL
    

* * *

## H04｜迁移与删除并发安全【P0】

迁移与删除同时发生时最终状态必须唯一且一致。

不得留下孤立 LabResult / ingestion。

*   PASS
    
*   FAIL
    

* * *

## H05｜迁移与目标档案 commit 的重复检测可串行【P0】

目标 HealthProfile 锁必须保证：

```

新 commit
+
迁入报告
```

不会在相同时间窗口静默绕过 duplicate 检查。

*   PASS
    
*   FAIL
    

* * *

# I. 正式报告删除数据库语义

## I01｜删除必须先验证 ownership【P0】

用户只能删除自己的报告。

*   PASS
    
*   FAIL
    

* * *

## I02｜删除 LabResult【P0】

删除正式报告后，该 report 对应：

```

LabResult = 0
```

*   PASS
    
*   FAIL
    

* * *

## I03｜删除 LabReport【P0】

正式 LabReport 物理删除。

*   PASS
    
*   FAIL
    

* * *

## I04｜删除 ConfirmationItem【P0】

包括：

*   OCR confirmation；
    
*   手工新增；
    
*   REMOVED 项。
    

全部删除。

*   PASS
    
*   FAIL
    

* * *

## I05｜删除全部 OcrResultItem【P0】

该 ingestion 所有 OCR runs 的结果全部删除。

*   PASS
    
*   FAIL
    

* * *

## I06｜删除全部 OcrTask【P0】

包括：

*   成功 run；
    
*   失败 run；
    
*   retry run。
    

全部删除。

*   PASS
    
*   FAIL
    

* * *

## I07｜删除 ReportAsset 数据库记录【P0】

删除后不得继续通过产品签发新 preview URL。

*   PASS
    
*   FAIL
    

* * *

## I08｜删除 UploadAuthorization【P0】

该 ingestion 对应上传授权记录清理。

*   PASS
    
*   FAIL
    

* * *

## I09｜删除 ReportIngestion【P0】

完整来源 ingestion 最终物理删除。

*   PASS
    
*   FAIL
    

* * *

## I10｜StandardMetric 不受影响【P0】

删除用户报告不得删除公共 StandardMetric。

*   PASS
    
*   FAIL
    

* * *

## I11｜删除采用单数据库事务【P0】

任意 DB 删除步骤异常：

```

所有 DB 医疗数据保持原状
```

*   PASS
    
*   FAIL
    

* * *

# J. COS 删除与 FileCleanup

## J01｜删除事务中创建 PREFIX cleanup【P0】

正式报告 DB 删除提交前必须存在：

```

FileCleanup(
  target_type=PREFIX,
  status=PENDING
)
```

*   PASS
    
*   FAIL
    

* * *

## J02｜清理目标为完整 ingestion prefix【P0】

必须覆盖：

```

users/{user_id}/ingestions/{ingestion_id}/
```

而不是仅当前 ReportAsset。

*   PASS
    
*   FAIL
    

* * *

## J03｜FileCleanup 创建失败则 DB 删除 rollback【P0】

不得：

```

DB 已删
但没有任何文件清理目标记录
```

*   PASS
    
*   FAIL
    

* * *

## J04｜DB commit 后即时尝试 COS cleanup【P0】

成功可以直接标记：

```

DONE
```

*   PASS
    
*   FAIL
    

* * *

## J05｜COS 即时失败不恢复正式报告【P0】

COS 删除失败时：

```

LabReport / LabResult 仍保持已删除
```

*   PASS
    
*   FAIL
    

* * *

## J06｜COS 即时失败仍返回正式删除成功【P0】

数据库事务已经成功时 DELETE API 不因后续 COS 临时错误向用户返回“报告仍存在”。

*   PASS
    
*   FAIL
    

* * *

## J07｜COS 失败保持 PENDING【P0】

FileCleanup 不得被错误标记 DONE。

*   PASS
    
*   FAIL
    

* * *

## J08｜PREFIX cleanup 可分页处理【P0】

对象数量超过单次 COS list 返回限制时仍能完整删除。

*   PASS
    
*   FAIL
    

* * *

## J09｜对象已经不存在视为成功【P0】

cleanup 必须幂等。

*   PASS
    
*   FAIL
    

* * *

## J10｜重复执行 PREFIX cleanup 安全【P0】

同一 cleanup 被重复处理不得报业务错误或恢复任何数据。

*   PASS
    
*   FAIL
    

* * *

## J11｜PENDING cleanup 有真实消费者【P0】

不能只在数据库留 PENDING。

必须存在可执行的后台 processor/worker 或等价可靠消费者。

*   PASS
    
*   FAIL
    

* * *

## J12｜历史 OBJECT cleanup 仍可处理【P0】

Stage 02 原有 FileCleanup 逻辑不能被 PREFIX 支持破坏。

*   PASS
    
*   FAIL
    

* * *

# K. 删除后的正式查询

## K01｜删除后报告列表立即消失【P0】

无需等待 COS cleanup。

*   PASS
    
*   FAIL
    

* * *

## K02｜删除后详情不可读取【P0】

报告正式详情不可继续访问。

*   PASS
    
*   FAIL
    

* * *

## K03｜删除后原图 API 不再签发新 URL【P0】

即使 COS cleanup 暂时 PENDING，也不得通过产品继续生成新的 preview URL。

*   PASS
    
*   FAIL
    

* * *

## K04｜删除后识别任务记录不重新出现【P0】

因为 source ingestion 已删除。

*   PASS
    
*   FAIL
    

* * *

## K05｜删除后 Stage 06 数据基础自然消失【P0】

数据库中对应 LabResult 已不存在。

不得建立额外“趋势删除同步”逻辑。

*   PASS
    
*   FAIL
    

* * *

# L. 权限与安全

## L01｜跨用户报告列表隔离【P0】

*   PASS
    
*   FAIL
    

* * *

## L02｜跨用户详情隔离【P0】

*   PASS
    
*   FAIL
    

* * *

## L03｜跨用户 asset 列表隔离【P0】

*   PASS
    
*   FAIL
    

* * *

## L04｜跨用户 preview 隔离【P0】

*   PASS
    
*   FAIL
    

* * *

## L05｜跨用户迁移隔离【P0】

*   PASS
    
*   FAIL
    

* * *

## L06｜跨用户删除不影响数据【P0】

*   PASS
    
*   FAIL
    

* * *

## L07｜普通 API 不返回永久 COS URL【P0】

*   PASS
    
*   FAIL
    

* * *

## L08｜普通 API 不暴露 COS Secret【P0】

*   PASS
    
*   FAIL
    

* * *

## L09｜日志不包含完整检验结果【P0】

*   PASS
    
*   FAIL
    

* * *

## L10｜Cleanup 日志不输出医疗全文【P0】

*   PASS
    
*   FAIL
    

* * *

# M. 小程序正式报告列表

## M01｜首页存在正式报告入口【P0】

*   PASS
    
*   FAIL
    

* * *

## M02｜列表使用当前默认 HealthProfile【P0】

*   PASS
    
*   FAIL
    

* * *

## M03｜切换 HealthProfile 后报告列表切换【P0】

*   PASS
    
*   FAIL
    

* * *

## M04｜列表支持 loading【P0】

*   PASS
    
*   FAIL
    

* * *

## M05｜列表支持 empty【P0】

*   PASS
    
*   FAIL
    

* * *

## M06｜列表支持 error/retry【P0】

*   PASS
    
*   FAIL
    

* * *

## M07｜列表支持加载更多【P0】

*   PASS
    
*   FAIL
    

* * *

## M08｜点击报告进入正式详情【P0】

*   PASS
    
*   FAIL
    

* * *

# N. 小程序报告详情与原图

## N01｜基本信息正确【P0】

*   PASS
    
*   FAIL
    

* * *

## N02｜正式结果列表正确【P0】

*   PASS
    
*   FAIL
    

* * *

## N03｜非数值结果正确【P0】

*   PASS
    
*   FAIL
    

* * *

## N04｜未关联 StandardMetric 项可查看【P0】

*   PASS
    
*   FAIL
    

* * *

## N05｜原始报告入口可达【P0】

*   PASS
    
*   FAIL
    

* * *

## N06｜多页原图顺序正确【P0】

*   PASS
    
*   FAIL
    

* * *

## N07｜原图可放大查看【P0】

*   PASS
    
*   FAIL
    

* * *

## N08｜原图加载失败有错误提示和重试【P0】

*   PASS
    
*   FAIL
    

* * *

# O. 小程序迁移与删除

## O01｜迁移只展示当前用户其它档案【P0】

*   PASS
    
*   FAIL
    

* * *

## O02｜迁移前有明确确认【P0】

*   PASS
    
*   FAIL
    

* * *

## O03｜duplicate 迁移有二次提示【P0】

*   PASS
    
*   FAIL
    

* * *

## O04｜用户可取消 duplicate 迁移【P0】

*   PASS
    
*   FAIL
    

* * *

## O05｜用户可明确继续 duplicate 迁移【P0】

*   PASS
    
*   FAIL
    

* * *

## O06｜迁移成功后详情归属刷新【P0】

*   PASS
    
*   FAIL
    

* * *

## O07｜删除必须二次确认【P0】

确认内容明确说明：

```

检验结果
原始图片
识别数据
```

都会删除且无法恢复。

*   PASS
    
*   FAIL
    

* * *

## O08｜删除成功返回列表并刷新【P0】

*   PASS
    
*   FAIL
    

* * *

# P. 现有入口收口

## P01｜首页不把 CONFIRMED 当当前 draft【P0】

*   PASS
    
*   FAIL
    

* * *

## P02｜当前 ingestion 只取未完成状态【P0】

至少：

```

UPLOADING
READY
QUEUED
PROCESSING
OCR_FAILED
PENDING_CONFIRMATION
```

*   PASS
    
*   FAIL
    

* * *

## P03｜识别任务记录与正式报告分离【P0】

已 commit 正式报告不再依赖识别任务页打开。

*   PASS
    
*   FAIL
    

* * *

## P04｜Stage 04 commit 后可查看正式报告【P0】

commit 成功后使用真实返回的：

```

report_id
```

进入正式详情。

*   PASS
    
*   FAIL
    

* * *

# Q. Stage 04 回归

## Q01｜Stage 04 commit 幂等仍通过【P0】

*   PASS
    
*   FAIL
    

* * *

## Q02｜REVIEW\_PENDING 阻断仍通过【P0】

*   PASS
    
*   FAIL
    

* * *

## Q03｜KEEP\_ORIGINAL\_NAME 仍通过【P0】

*   PASS
    
*   FAIL
    

* * *

## Q04｜纯手工报告仍可 commit【P0】

*   PASS
    
*   FAIL
    

* * *

## Q05｜疑似重复保存仍通过【P0】

*   PASS
    
*   FAIL
    

* * *

## Q06｜OcrResultItem 不可变仍通过【P0】

*   PASS
    
*   FAIL
    

* * *

## Q07｜原有私有 COS preview 未被破坏【P0】

*   PASS
    
*   FAIL
    

* * *

# R. Backend 自动验证

## R01｜Backend Tests【P0】

从 `backend` 运行：

```

.venv/Scripts/python.exe -m pytest -q
```

所有现有 + Stage 05 测试通过。

不得删除、skip 或弱化 Stage 00～04 测试制造 PASS。

*   PASS
    
*   FAIL
    

* * *

## R02｜Backend Ruff【P0】

从 `backend` 运行：

```

.venv/Scripts/ruff.exe check . --no-cache
```

或仓库当前等价命令。

*   PASS
    
*   FAIL
    

* * *

# S. PostgreSQL 17 集成验证

## S01｜0004 → 0005 migration【P0】

真实 PostgreSQL 17 临时数据库：

```

0004_confirmation_report
→ 0005_report_management
```

通过。

*   PASS
    
*   FAIL
    

* * *

## S02｜空库完整 migration【P0】

```

0001
→ 0002
→ 0003
→ 0004
→ 0005
```

通过。

*   PASS
    
*   FAIL
    

* * *

## S03｜Stage 04 既有正式报告升级后可直接查询【P0】

*   PASS
    
*   FAIL
    

* * *

## S04｜迁移事务 rollback【P0】

*   PASS
    
*   FAIL
    

* * *

## S05｜迁移并发一致性【P0】

*   PASS
    
*   FAIL
    

* * *

## S06｜迁移 vs 删除并发【P0】

*   PASS
    
*   FAIL
    

* * *

## S07｜删除事务 rollback【P0】

*   PASS
    
*   FAIL
    

* * *

## S08｜删除完整链路核对【P0】

删除后至少核对：

```

LabResult = 0
LabReport = 0
ConfirmationItem = 0
OcrResultItem = 0
OcrTask = 0
ReportAsset = 0
UploadAuthorization = 0
ReportIngestion = 0
```

对应本报告 ingestion。

*   PASS
    
*   FAIL
    

* * *

## S09｜FileCleanup PREFIX 保留【P0】

删除 DB 成功后：

```

PENDING 或 DONE
```

cleanup 记录存在。

*   PASS
    
*   FAIL
    

* * *

## S10｜临时测试数据库全部删除【P0】

集成脚本结束后不得遗留 Stage 05 测试数据库。

*   PASS
    
*   FAIL
    

* * *

# T. Miniapp 自动验证

## T01｜Miniapp Tests【P0】

运行：

```

pnpm test
```

*   PASS
    
*   FAIL
    

* * *

## T02｜Miniapp Typecheck【P0】

运行：

```

pnpm typecheck
```

*   PASS
    
*   FAIL
    

* * *

## T03｜Miniapp Build【P0】

运行：

```

pnpm build:mp-weixin
```

*   PASS
    
*   FAIL
    

* * *

# U. Admin 回归

## U01｜Admin Typecheck【P0】

运行：

```

pnpm typecheck
```

*   PASS
    
*   FAIL
    

* * *

## U02｜Admin Build【P0】

运行：

```

pnpm build
```

*   PASS
    
*   FAIL
    

* * *

# V. 真实微信小程序人工验收

以下必须由项目负责人实际执行。

Codex、自动测试、API 调用或构建成功不能替代本节。

* * *

## V01｜正式报告列表完整流程【P0】

使用至少一份已经 Stage 04 commit 的正式报告。

验证：

```

进入首页
→ 检验报告
→ 当前 HealthProfile 报告列表
```

检查：

*   正式报告出现；
    
*   未 commit 任务不出现；
    
*   日期正确；
    
*   医院正确；
    
*   项目数量正确；
    
*   abnormal 提示合理；
    
*   切换健康档案后数据切换。
    
*   PASS
    
*   FAIL
    

* * *

## V02｜正式报告详情【P0】

进入真实正式报告。

人工核对：

*   报告基本信息；
    
*   数值结果；
    
*   非数值结果；
    
*   单位；
    
*   参考范围；
    
*   abnormal；
    
*   有 StandardMetric 项；
    
*   至少一个未关联 StandardMetric 项，如现有测试数据具备；
    
*   顺序与 Stage 04 保存结果一致。
    

不得出现正式结果编辑入口。

*   PASS
    
*   FAIL
    

* * *

## V03｜原始报告查看【P0】

使用多页报告验证：

```

正式详情
→ 查看原始报告
→ 多页打开
→ 放大
→ 返回
```

要求：

*   顺序正确；
    
*   原图正确；
    
*   返回详情正常；
    
*   再次进入仍可使用。
    
*   PASS
    
*   FAIL
    

* * *

## V04｜正式报告迁移【P0】

执行真实：

```

本人
→ 父亲
```

或其它本人管理的两个测试 HealthProfile。

确认：

```

源档案列表消失
目标档案列表出现
详情正式值未变化
原图仍能查看
```

*   PASS
    
*   FAIL
    

* * *

## V05｜疑似重复迁移【P0】

准备目标档案存在疑似重复正式报告的场景。

验证：

```

迁移
→ duplicate 提示
→ 取消
```

报告不迁移。

再次：

```

迁移
→ duplicate 提示
→ 仍然迁移
```

报告成功迁移，原报告未被覆盖。

*   PASS
    
*   FAIL
    

* * *

## V06｜正式报告删除【P0】

选择测试报告：

```

详情
→ 删除
→ 明确二次确认
→ 删除成功
```

确认：

*   报告从列表立即消失；
    
*   原详情不能重新打开；
    
*   正式原图入口不能重新访问；
    
*   已删除报告不重新出现在识别任务记录；
    
*   其它报告不受影响。
    

COS 异常补偿不要求负责人通过人为制造生产 COS 故障进行人工验证，由自动/集成测试承担。

*   PASS
    
*   FAIL
    

* * *

# W. Stage 06 / Stage 07 边界

## W01｜未实现我的指标【P0】

不得新增 Stage 06 正式：

```

我的指标
```

页面/API。

*   PASS
    
*   FAIL
    

* * *

## W02｜未实现指标历史【P0】

*   PASS
    
*   FAIL
    

* * *

## W03｜未实现趋势折线图【P0】

*   PASS
    
*   FAIL
    

* * *

## W04｜未实现关注指标【P0】

*   PASS
    
*   FAIL
    

* * *

## W05｜未实现单位趋势分组【P0】

*   PASS
    
*   FAIL
    

* * *

## W06｜未实现 StandardMetric 管理后台【P0】

*   PASS
    
*   FAIL
    

* * *

## W07｜未实现 MetricAlias 管理【P0】

*   PASS
    
*   FAIL
    

* * *

## W08｜未实现 OCR 管理后台业务【P0】

*   PASS
    
*   FAIL
    

* * *

## W09｜未修改 OCR 算法规则【P0】

不得修改：

*   AUTO/REVIEW threshold；
    
*   Retry/Evidence 算法；
    
*   OCR metric matching；
    
*   OCR Pipeline 判定逻辑
    

来完成 Stage 05。

*   PASS
    
*   FAIL
    

* * *

# X. 文档与 RESULT

## X01｜必要基线与 README 保持一致【P0】

如果 Stage 05 实际增加长期运行的 FileCleanup worker，应同步必要技术说明。

README 至少反映：

```

Stage 05 正式报告管理已实现/当前验收状态
```

*   PASS
    
*   FAIL
    

* * *

## X02｜Stage 05 RESULT.md 完整【P0】

最终 RESULT 至少记录：

*   实际完成项；
    
*   实际修改文件；
    
*   migration；
    
*   report API；
    
*   正式详情数据边界；
    
*   迁移实现；
    
*   duplicate 迁移实现；
    
*   删除范围；
    
*   FileCleanup PREFIX；
    
*   COS 即时清理与 retry；
    
*   PostgreSQL 集成；
    
*   自动测试；
    
*   小程序构建；
    
*   人工验收结果；
    
*   已知问题；
    
*   设计偏差；
    
*   Stage 06 边界。
    
*   PASS
    
*   FAIL
    

* * *

## X03｜人工验收未完成前不得标 PASS【P0】

即使：

```

pytest
Ruff
PostgreSQL
Miniapp tests
typecheck
build
```

全部通过，只要 V01～V06 尚未由项目负责人真实微信人工验收：

```

Stage 05 仍不得判定 PASS
```

*   PASS
    
*   FAIL
    

* * *

# Z. 最终判定

Stage 05 只有以下全部满足才能：

```

Stage 05 = PASS
```

必须同时满足：

```

A～X 全部 P0 PASS

+

正式报告列表只读取正式数据
+
HealthProfile 隔离正确
+
分页与检验时间排序正确

+

正式详情完整
+
非数值结果正确
+
abnormal 不重新推断
+
正式结果不可编辑

+

原图完整追溯
+
COS 私有短时访问

+

整份报告迁移
+
LabReport / LabResult / ReportIngestion 三处一致
+
目标档案重新查重
+
重复只提示不阻断
+
事务与并发安全

+

正式报告完整硬删除
+
确认/OCR/原图数据库链完整清除
+
COS ingestion prefix 清理
+
FileCleanup 可靠持久化
+
COS 失败可恢复重试
+
删除后正式数据立即退出查询

+

跨用户五类操作隔离

+

Stage 04 全量回归

+

PostgreSQL 17 migration / transaction / concurrency PASS

+

Backend Tests PASS
+
Ruff PASS
+
Miniapp Tests PASS
+
Miniapp Typecheck PASS
+
Miniapp Build PASS
+
Admin Typecheck/Build PASS

+

负责人真实微信 V01～V06 全部 PASS

+

RESULT.md 完整

+

Stage 06 / Stage 07 未提前实现
```

任意 P0 未完成：

```

Stage 05 = FAIL
```

不得使用：

```

页面能打开
Mock 成功
SQLite 单测通过
接口基本可用
COS 正常情况下能删
```

替代 Stage 05 正式验收闭环。