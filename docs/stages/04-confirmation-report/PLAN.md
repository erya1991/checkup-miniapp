# Stage 04｜检验结果人工确认与正式报告生成

**状态：READY\_FOR\_IMPLEMENTATION**

## 1\. 阶段目标

Stage 04 承接已经验收通过的 Stage 03。

Stage 03 已完成：

```

ReportIngestion.READY
→ OcrTask
→ OCR Worker
→ OcrResultItem
→ FINAL_AUTO / FINAL_REVIEW
→ ReportIngestion.PENDING_CONFIRMATION
```

Stage 04 的职责是把 Stage 03 产生的**不可变 OCR 机器快照**安全转换为用户可编辑的确认工作区，并在报告信息、REVIEW 项、人工修改、漏识别补录、标准指标映射和疑似重复提示等确认工作完成后，由用户显式执行最终 commit，生成正式 `LabReport / LabResult`。

本阶段结束时必须形成真实链路：

```

ReportIngestion.PENDING_CONFIRMATION
→ 初始化 ConfirmationItem
→ 用户确认报告基本信息
→ FINAL_AUTO 默认采用
→ FINAL_REVIEW 全部人工处理
→ 用户可主动修改 AUTO
→ 用户可手工补充漏识别指标
→ 疑似重复检测
→ 用户最终确认 commit
→ 单一数据库事务
→ LabReport
→ LabResult × N
→ ReportIngestion.CONFIRMED
```

Stage 04 的核心产物是：

> **经过用户最终确认、可完整追溯、可以进入后续正式报告管理和指标历史的数据。**

Stage 04 是 OCR 临时域与正式健康数据域之间的安全闸门。

* * *

## 2\. 必读基线

实施前必须按 `AGENTS.md` 顺序读取：

1.  根目录 `AGENTS.md`；
    
2.  `docs/00-baseline/PRODUCT_BASELINE.md`；
    
3.  `docs/00-baseline/TECH_BASELINE.md`；
    
4.  `docs/00-baseline/DEVELOPMENT_RULES.md`；
    
5.  本目录 `PLAN.md`；
    
6.  本目录 `ACCEPTANCE.md`；
    
7.  `docs/stages/03-ocr-integration/RESULT.md`；
    
8.  本阶段涉及数据确认、正式数据生成与 OCR 边界，继续读取：
    
    *   `docs/01-architecture/DATA_MODEL.md`
        
    *   `docs/01-architecture/API_CONVENTIONS.md`
        
    *   `docs/01-architecture/SYSTEM_ARCHITECTURE.md`
        
    *   `docs/01-architecture/OCR_INTEGRATION.md`
        

不得重新实现 Stage 00～03 已验收能力，也不得因为 Stage 04 需要确认数据而修改 OCR 算法安全判定。

* * *

## 3\. Stage 03 已知真实基础

Stage 03 已于 2026-09-29 验收通过。

当前真实工程已经具备：

*   `ReportIngestion`；
    
*   `ReportAsset`；
    
*   私有 Tencent COS 原始报告；
    
*   `OcrTask`；
    
*   PostgreSQL 持久化 OCR 队列；
    
*   独立 OCR Worker；
    
*   已验证 OCR Pipeline；
    
*   OCR Artifact 私有 COS 留存；
    
*   不可变 `OcrResultItem`；
    
*   `FINAL_AUTO / FINAL_REVIEW`；
    
*   OCR 成功终态 `ReportIngestion.PENDING_CONFIRMATION`；
    
*   小程序 OCR 处理页；
    
*   ingestion task 历史列表；
    
*   原图短时鉴权预览；
    
*   Worker lease / retry / 故障恢复；
    
*   跨用户、跨健康档案隔离。
    

当前真实代码中：

```

ConfirmationItem   不存在
LabReport          不存在
LabResult          不存在
StandardMetric     不存在
```

`OcrTask.report_candidates` 字段已存在，但当前正式 OCR adapter 尚未稳定输出报告级候选，实际可以为空。

因此 Stage 04 不得假定医院、检验日期、报告编号已经能够由 OCR 自动填写。

* * *

# 4\. 阶段职责与硬边界

## 4.1 Stage 04 负责“正式数据诞生”

本阶段负责：

```

OcrResultItem
→ ConfirmationItem
→ 用户人工确认
→ 疑似重复提示
→ commit
→ LabReport
→ LabResult
```

只有 commit 成功后的：

```

LabReport
LabResult
```

属于正式健康数据。

以下均不属于正式健康数据：

```

OcrResultItem
ConfirmationItem
OcrTask.report_candidates
```

这些数据不得进入未来报告历史、指标历史和趋势查询。

* * *

## 4.2 OcrResultItem 永远不可被人工覆盖

`OcrResultItem` 表示：

> 机器当时实际识别和判断了什么。

Stage 04 必须遵守：

*   不为用户提供修改 OcrResultItem 的 API；
    
*   人工修改只写 `ConfirmationItem`；
    
*   删除错误识别不 DELETE OcrResultItem；
    
*   选择标准指标不 UPDATE OcrResultItem；
    
*   commit 不 UPDATE OcrResultItem；
    
*   原始图片、OCR Artifact、OcrResultItem 永远保留机器事实。
    

* * *

## 4.3 ConfirmationItem 是可编辑工作区

`ConfirmationItem` 表示：

> 用户最终准备提交的候选结果。

用户在 commit 前可以：

*   接受；
    
*   修改；
    
*   选择标准指标；
    
*   按原名称保存；
    
*   删除错误识别；
    
*   手工新增漏识别项目。
    

commit 后 ConfirmationItem 冻结，不再作为可编辑工作区。

Stage 04 不建设复杂编辑历史版本系统。

本阶段必须保证的追溯链为：

```

机器原始事实
OcrResultItem

↓

用户最终确认候选
ConfirmationItem

↓

正式保存值
LabResult
```

不要求记录用户每一次输入框按键或中间编辑版本。

* * *

## 4.4 Stage 04 与 Stage 05 边界

Stage 04：

*   人工确认；
    
*   报告基本信息；
    
*   REVIEW resolved；
    
*   AUTO 主动修改；
    
*   手工补项；
    
*   纯手工兜底；
    
*   StandardMetric 最小只读能力；
    
*   疑似重复提示；
    
*   commit；
    
*   创建 LabReport / LabResult。
    

Stage 05：

*   正式报告列表；
    
*   正式报告详情；
    
*   正式原始报告查看入口；
    
*   正式报告删除；
    
*   已保存报告所属档案迁移；
    
*   正式报告管理体验。
    

Stage 04 commit 成功后只需要提供最小成功反馈，不提前建设 Stage 05 报告列表或详情。

* * *

# 5\. ReportIngestion 状态机

继续使用现有主状态：

```

UPLOADING
↕
READY
↓
QUEUED
↓
PROCESSING
↓
PENDING_CONFIRMATION
↓
CONFIRMED
```

异常：

```

QUEUED / PROCESSING
↓
OCR_FAILED
```

Stage 04 不新增：

```

CONFIRMING
PARTIALLY_CONFIRMED
READY_TO_COMMIT
```

是否可以 commit 由 Confirmation 工作区实时计算。

### 状态语义

`PENDING_CONFIRMATION`：

*   OCR 已成功，或已进入纯手工确认模式；
    
*   允许编辑报告信息；
    
*   允许编辑 ConfirmationItem；
    
*   尚未生成正式报告。
    

`CONFIRMED`：

*   commit 已成功；
    
*   已存在唯一正式 LabReport；
    
*   Confirmation 工作区冻结；
    
*   不再允许 Stage 04 编辑。
    

* * *

# 6\. Confirmation 工作区初始化

## 6.1 OCR 报告初始化来源

对于：

```

ReportIngestion.status = PENDING_CONFIRMATION
ReportIngestion.mode = OCR
```

必须从该 ingestion 对应的成功 OCR run 初始化 ConfirmationItem。

来源必须是：

```

OcrTask.status = SUCCEEDED
→ OcrResultItem
```

不得直接从 OCR Artifact JSON 临时重新解析生成确认数据。

* * *

## 6.2 初始化必须幂等

Stage 03 已经存在真实 `PENDING_CONFIRMATION` 数据，但尚无 ConfirmationItem。

因此 Stage 04 必须兼容既有任务。

建议统一实现：

```

ensure_confirmation_workspace()
```

该逻辑可由：

```

OCR 成功后的后续初始化
+
首次 GET confirmation 时的幂等补偿
```

共同调用。

必须保证：

*   同一 OcrResultItem 最多生成 1 个 ConfirmationItem；
    
*   重复进入确认页不重复创建；
    
*   API 并发请求不重复创建；
    
*   Stage 03 已产生的老任务无需重新 OCR。
    

数据库层必须存在相应唯一约束。

* * *

## 6.3 初始化必须原子化

初始化时建议锁定当前 ingestion。

如果发生：

*   成功 OcrTask 不存在；
    
*   OcrResultItem 不完整；
    
*   来源关系不一致；
    
*   中途数据库异常；
    

则：

*   不允许生成半套 ConfirmationItem；
    
*   ingestion 保持原状态；
    
*   返回稳定业务错误；
    
*   不修改 OcrResultItem。
    

* * *

# 7\. ConfirmationItem 数据模型

本阶段新增正式 `ConfirmationItem`。

至少需要表达：

### 基础关系

*   `id`
    
*   `ingestion_id`
    
*   `source_ocr_result_item_id`，手工新增时为空
    
*   `sequence_no`
    
*   `created_at`
    
*   `updated_at`
    

关键约束：

```

UNIQUE(source_ocr_result_item_id)
```

对于 NULL 的手工新增项允许存在多条。

* * *

## 7.1 最终候选字段

至少保存：

*   `metric_name`
    
*   `result_text`
    
*   `result_numeric`（可空）
    
*   `comparator`（可空）
    
*   `unit_original` 或等价最终单位文本
    
*   `unit_normalized`（可空）
    
*   `reference_text`
    
*   `reference_low`（可空）
    
*   `reference_high`（可空）
    
*   `abnormal`（可空）
    
*   `standard_metric_id`（可空）
    

最终具体字段名可根据当前 ORM 风格调整，但必须保证：

*   非数值结果可以保存；
    
*   单位可以为空；
    
*   参考范围可以为空；
    
*   standard metric 可以为空。
    

* * *

## 7.2 source\_type

至少：

```

OCR_AUTO
OCR_CORRECTED
MANUAL
```

含义：

`OCR_AUTO`：

*   来自 FINAL\_AUTO；
    
*   用户没有修改结构化结果；
    
*   默认采用。
    

`OCR_CORRECTED`：

*   来自 OCR；
    
*   用户主动修改了候选数据。
    

`MANUAL`：

*   用户手工新增；
    
*   或纯手工报告中的项目。
    

* * *

## 7.3 review\_status

至少：

```

PENDING
RESOLVED
```

初始化：

```

FINAL_AUTO
→ RESOLVED

FINAL_REVIEW
→ PENDING
```

AUTO 不要求逐项点击确认，但整份报告仍必须由用户最终 commit。

* * *

## 7.4 resolution

至少支持：

```

ACCEPTED
CORRECTED
STANDARD_METRIC_SELECTED
KEEP_ORIGINAL_NAME
MANUAL_ADDED
REMOVED
```

其中：

*   `ACCEPTED`：用户确认原候选正确；
    
*   `CORRECTED`：人工修改；
    
*   `STANDARD_METRIC_SELECTED`：用户明确选择标准指标；
    
*   `KEEP_ORIGINAL_NAME`：不关联标准指标，按当前名称正式保存；
    
*   `MANUAL_ADDED`：漏识别或纯手工新增；
    
*   `REMOVED`：用户确认是错误识别，正式报告不生成对应 LabResult。
    

* * *

# 8\. OCR → ConfirmationItem 初始化规则

## 8.1 FINAL\_AUTO

初始化：

```

review_status = RESOLVED
source_type = OCR_AUTO
resolution = ACCEPTED
```

默认采用 Pipeline 已形成的最终候选。

AUTO 不要求用户逐行点击。

* * *

## 8.2 FINAL\_REVIEW

初始化：

```

review_status = PENDING
source_type = OCR_CORRECTED 或待最终处理状态
resolution = NULL
```

在用户明确处理之前不得视为 resolved。

不得因为页面打开、滚动经过、查看原图而自动 resolved。

* * *

## 8.3 字段初始化原则

不得简单只复制 `raw_*`。

应优先使用 OcrResultItem 中已经经过 Pipeline 结构化处理后的最终候选：

*   `result_text`
    
*   `result_numeric`
    
*   `comparator`
    
*   `normalized_unit`
    
*   `reference_text`
    
*   `reference_low`
    
*   `reference_high`
    
*   `abnormal`
    

同时指标名称应保留报告原始语义，原则上使用 OCR 行原始指标名称作为 `metric_name`。

StandardMetric 身份与原报告显示名称必须是两个不同概念：

```

metric_name
= 原报告中的名称

standard_metric_id
= 跨医院统一标准指标身份
```

不得为了标准化覆盖报告原始项目名。

* * *

# 9\. 报告级信息确认

Stage 04 必须让用户确认正式报告级信息。

建议在 `ReportIngestion` 增加临时确认字段：

*   `hospital_name`，可空；
    
*   `examination_date`，commit 前必填；
    
*   `examination_time`，可空；
    
*   `report_no`，可空；
    
*   `report_category`，可空；
    
*   `confirmation_initialized_at`；
    
*   `duplicate_status`；
    
*   `confirmed_at`。
    

字段具体命名可根据现有风格调整。

* * *

## 9.1 检验日期与时间

正式趋势时间必须来源于：

```

examination_date
+
examination_time（如存在）
```

不得使用：

*   上传时间；
    
*   ingestion 创建时间；
    
*   OCR 时间；
    
*   commit 时间；
    
*   LabReport.created\_at。
    

建议：

```

examination_date = DATE
examination_time = TIME NULL
```

因为大量实际报告只有日期，没有具体时间。

同一天多次报告允许全部保存，不覆盖、不合并、不平均。

* * *

## 9.2 OCR 报告级候选边界

当前 `OcrTask.report_candidates` 可以为空。

如果 Pipeline 提供可靠候选，可以预填到确认页面。

如果没有：

*   医院允许用户填写；
    
*   检验日期必须用户填写；
    
*   报告编号允许用户填写；
    
*   不得在业务层重新从 OCR 全文猜测。
    

Stage 04 不重新开启报告级 OCR 算法研发。

* * *

# 10\. REVIEW 项处理

每个 `FINAL_REVIEW` 必须由用户明确完成以下一种处理后，才能进入 RESOLVED。

## 10.1 确认正确

用户核对原图认为当前候选无误：

```

review_status = RESOLVED
resolution = ACCEPTED
```

不修改 OcrResultItem。

* * *

## 10.2 人工修改

允许修改：

*   指标名称；
    
*   结果；
    
*   单位；
    
*   参考范围；
    
*   标准指标关联。
    

保存后：

```

review_status = RESOLVED
resolution = CORRECTED
source_type = OCR_CORRECTED
```

* * *

## 10.3 选择标准指标

用户可明确选择：

```

standard_metric_id
```

如果没有同时修改其它结果值，可记录：

```

resolution = STANDARD_METRIC_SELECTED
```

如果同时进行了人工修改，可使用：

```

resolution = CORRECTED
```

不需要为多个组合操作设计复杂状态枚举。

* * *

## 10.4 按原名称保存

用户明确选择：

```

按原名称保存
```

则：

```

standard_metric_id = NULL
review_status = RESOLVED
resolution = KEEP_ORIGINAL_NAME
```

该结果：

*   可以正式保存；
    
*   可以在报告详情中显示；
    
*   可以进入普通报告历史；
    
*   不得进入 StandardMetric 跨报告趋势聚合。
    

* * *

## 10.5 删除错误识别

不得物理 DELETE ConfirmationItem。

应：

```

review_status = RESOLVED
resolution = REMOVED
```

commit 时跳过。

追溯关系必须保留：

```

OcrResultItem
→ ConfirmationItem.REMOVED
→ 无 LabResult
```

* * *

# 11\. AUTO 项主动修改

FINAL\_AUTO 默认采用，但用户必须可以主动编辑。

用户修改 AUTO 后：

```

source_type:
OCR_AUTO → OCR_CORRECTED

resolution:
CORRECTED
```

`review_status` 保持：

```

RESOLVED
```

不得把 AUTO 设计成只读。

* * *

# 12\. 人工编辑后的结构化字段处理

用户修改结果、单位或参考范围后，不得继续盲目沿用 OCR 时的旧结构化字段。

至少满足：

1.  `result_text` 永远保留用户确认后的文本；
    
2.  如果可以安全解析简单数值/比较符，可以更新：
    
    *   `result_numeric`
        
    *   `comparator`
        
3.  无法安全解析时：
    
    *   保留 `result_text`
        
    *   `result_numeric = NULL`
        
4.  参考范围同理：
    
    *   可安全解析则保存 low/high；
        
    *   否则只保留 `reference_text`
        
5.  用户修改结果或参考范围后，旧 abnormal 不能无条件继续沿用；
    
6.  只有在能够确定时才重新计算 abnormal，否则允许为空。
    

Stage 04 不为此建设新的医学算法或复杂单位转换系统。

* * *

# 13\. 手工新增漏识别指标

确认页面必须提供：

```

+ 添加漏识别项目
```

至少允许录入：

*   指标名称；
    
*   结果；
    
*   单位；
    
*   参考范围；
    
*   标准指标，可空。
    

新增：

```

source_ocr_result_item_id = NULL
source_type = MANUAL
review_status = RESOLVED
resolution = MANUAL_ADDED
```

手工项允许后续再次编辑。

commit 时与其它非 REMOVED ConfirmationItem 一样生成 LabResult。

* * *

# 14\. 纯手工报告兜底

纯手工报告属于 V1.0 P0，本阶段实现最小可用兜底。

## 14.1 核心原则

“纯手工报告”表示：

> 结构化数据完全由用户手工录入。

不表示：

> 可以脱离原始报告凭记忆创建健康数据。

V1.0 仍要求至少存在 1 张有效原始 `ReportAsset`。

* * *

## 14.2 手工流程

允许：

```

上传原始报告图片
→ 选择手工录入
→ ReportIngestion.mode = MANUAL
→ PENDING_CONFIRMATION
→ 填写报告信息
→ 手工新增 1..N 个 ConfirmationItem
→ commit
```

也允许 OCR 明确失败后：

```

OCR_FAILED
→ 用户选择“转为手工录入”
→ 保留原始 ReportAsset
→ mode = MANUAL
→ PENDING_CONFIRMATION
```

不得要求用户为了手工兜底重新上传同一份图片。

* * *

## 14.3 不允许的转换

OCR 已成功并已有 Confirmation 工作区时，不需要转换为 MANUAL。

用户可以直接：

*   修改 OCR 项；
    
*   删除错误 OCR 项；
    
*   手工新增漏识别项。
    

* * *

# 15\. 最小 StandardMetric 正式基础数据

Stage 04 需要实现人工选择标准指标，因此必须引入最小正式 `StandardMetric`。

至少字段：

*   `id`
    
*   `code`
    
*   `name`
    
*   `status`
    
*   `created_at`
    
*   `updated_at`
    

关键约束：

```

code UNIQUE
```

* * *

## 15.1 本阶段只做只读主数据

Stage 04 支持：

*   根据名称搜索；
    
*   根据 code 搜索；
    
*   ConfirmationItem 关联。
    

Stage 04 不做：

*   StandardMetric 管理后台；
    
*   MetricAlias 管理后台；
    
*   用户自行创建全局标准指标；
    
*   OCR 在线配置。
    

* * *

## 15.2 与 PoC 指标库的边界

Stage 03 OCR runtime 中已有算法使用的 `metric_library.json`。

Stage 04 不得：

```

运行时自动把 metric_library.json 反写数据库
```

也不得：

```

发现未知 OCR code
→ 自动创建正式 StandardMetric
```

正式 StandardMetric 必须采用：

> 经过明确审核、版本可追踪的产品侧 seed 数据。

初始 seed 可以参考冻结 PoC 指标库中已验证的标准指标身份，但迁入后属于正式产品基础数据，与 OCR runtime 解耦。

* * *

## 15.3 OCR 候选映射

初始化 ConfirmationItem 时：

```

OcrResultItem.standard_metric_code
```

如果能够匹配正式 StandardMetric：

```

→ standard_metric_id
```

如果不能匹配：

```

standard_metric_id = NULL
```

不得自动创建正式指标。

对于 FINAL\_REVIEW，用户必须通过：

```

选择标准指标
或
按原名称保存
```

完成该类 unresolved 问题。

* * *

# 16\. 报告所属 HealthProfile 调整

正式保存前允许用户调整报告所属 HealthProfile。

规则：

1.  只能选择当前 User 自己拥有的 ACTIVE HealthProfile；
    
2.  不允许改变 ingestion.user\_id；
    
3.  原始 COS object key 不需要迁移；
    
4.  ConfirmationItem 不需要重新初始化；
    
5.  修改档案后疑似重复判断必须基于新档案重新计算；
    
6.  commit 后的正式报告档案迁移属于 Stage 05。
    

* * *

# 17\. 疑似重复报告

Stage 04 需要完成轻量、确定性的疑似重复提示。

只比较：

```

当前 User
+
当前 HealthProfile
+
已经正式 commit 的 LabReport
```

不得跨用户比较并泄露任何信息。

* * *

## 17.1 V1.0 推荐判断方式

优先采用确定性组合规则，不建设 AI 去重模型。

至少支持以下两类候选：

### 强标识规则

同一 HealthProfile，且：

```

非空 report_no 相同
```

并结合医院信息进行合理规范化判断。

### 组合规则

同一 HealthProfile，且：

```

examination_date 相同
+
医院相同或高度确定一致
+
指标集合高度重合
```

指标集合优先使用：

```

standard_metric_id
```

没有 StandardMetric 时，可使用规范化后的 `metric_name`。

具体阈值必须保持简单、可测试，并在 RESULT 中记录最终实现。

不得因为缺少报告号直接判定“不是重复”。

* * *

## 17.2 用户行为

发现疑似重复时：

*   提示；
    
*   展示已有报告最小摘要；
    
*   不自动覆盖旧报告；
    
*   不直接禁止保存；
    
*   用户可以返回修改；
    
*   用户可以明确选择“仍然保存”。
    

Stage 04 不建设正式报告详情页面。

重复提示中可以展示：

*   医院；
    
*   检验日期；
    
*   报告编号；
    
*   项目数；
    
*   必要的重复依据摘要。
    

* * *

## 17.3 重复确认必须绑定当前数据

如果用户在重复提示后修改：

*   HealthProfile；
    
*   医院；
    
*   日期；
    
*   报告编号；
    
*   ConfirmationItem；
    
*   StandardMetric 关联；
    

之前的重复确认必须失效或重新计算。

实现可以采用确认版本、数据 fingerprint 等简单机制。

不得出现：

```

先确认旧数据重复提示
→ 修改报告
→ 仍沿用旧 acknowledgement 无条件 commit
```

* * *

# 18\. commit 准入条件

统一实现 commit validation。

只有同时满足以下条件才允许生成正式报告：

```

ReportIngestion.status = PENDING_CONFIRMATION
```

且：

1.  ingestion 属于当前 User；
    
2.  HealthProfile 属于当前 User 且 ACTIVE；
    
3.  Confirmation 工作区已经完整初始化；
    
4.  `examination_date` 存在且合法；
    
5.  所有 OCR `FINAL_REVIEW` 对应 ConfirmationItem 均为 RESOLVED；
    
6.  不存在因初始化异常缺失的 OCR ConfirmationItem；
    
7.  至少存在 1 条非 REMOVED ConfirmationItem；
    
8.  每条正式保留项 `metric_name` 非空；
    
9.  每条正式保留项 `result_text` 非空；
    
10.  standard\_metric\_id 可以为空；
     
11.  疑似重复存在时已经完成针对当前数据的明确确认；
     
12.  当前 ingestion 尚未被其它事务生成第二份正式报告。
     

AUTO 项无需逐项点击确认。

用户执行最终 commit 即表示：

> 对整份报告，包括默认采用的 AUTO 项，完成最终确认。

* * *

# 19\. commit 事务性

commit 必须在单一 PostgreSQL 数据库事务内完成。

建议事务逻辑：

```

BEGIN

SELECT ReportIngestion FOR UPDATE

检查用户所有权
检查当前状态

如果已经 CONFIRMED：
    返回已有 LabReport
    不重复生成

锁定/读取 ConfirmationItem
再次执行全部 commit validation

执行疑似重复最终检查

创建 LabReport

遍历所有非 REMOVED ConfirmationItem
    创建 LabResult

更新 ReportIngestion:
    status = CONFIRMED
    confirmed_at = now

COMMIT
```

任何一步失败必须整体 rollback。

不得出现：

```

LabReport 已创建
但 LabResult 只有一半
```

或：

```

ingestion 已 CONFIRMED
但正式结果未完整保存
```

commit 事务中不进行 COS 上传、复制或其它分布式文件操作。

* * *

# 20\. commit 幂等

数据库层必须有硬约束：

```

LabReport.source_ingestion_id UNIQUE
```

建议：

```

LabResult.source_confirmation_item_id UNIQUE
```

重复：

```

POST /ingestions/{id}/commit
```

必须：

*   返回已经存在的同一 LabReport；
    
*   不创建第二份正式报告；
    
*   不创建重复 LabResult。
    

必须覆盖：

*   用户双击；
    
*   网络超时重试；
    
*   并发两个 commit 请求。
    

* * *

# 21\. LabReport

本阶段新增正式 `LabReport`。

至少表达：

*   `id`
    
*   `user_id`
    
*   `health_profile_id`
    
*   `source_ingestion_id`
    
*   `hospital_name`
    
*   `examination_date`
    
*   `examination_time`
    
*   `report_no`
    
*   `report_category`
    
*   `has_manual_correction`
    
*   `has_manual_items`
    
*   `created_at`
    
*   `updated_at`
    

必须：

```

UNIQUE(source_ingestion_id)
```

LabReport 的报告信息来源于 commit 时的 ReportIngestion 确认字段，而不是重新读取 OCR 候选。

* * *

# 22\. LabResult

本阶段新增正式 `LabResult`。

每个：

```

ConfirmationItem.resolution != REMOVED
```

生成一条 LabResult。

至少表达：

*   `id`
    
*   `report_id`
    
*   `health_profile_id`
    
*   `source_confirmation_item_id`
    
*   `sequence_no`
    
*   `metric_name`
    
*   `standard_metric_id`，可空
    
*   `result_text`
    
*   `result_numeric`，可空
    
*   `comparator`，可空
    
*   `unit_original`
    
*   `unit_normalized`，可空
    
*   `reference_text`
    
*   `reference_low`，可空
    
*   `reference_high`，可空
    
*   `abnormal`，可空
    
*   `data_source`
    
*   `examination_date`
    
*   `examination_time`
    
*   `created_at`
    

最终字段可以结合现有 SQLAlchemy 风格调整，但必须满足未来 Stage 05 / 06 的查询需要。

* * *

## 22.1 data\_source

至少：

```

OCR_AUTO
OCR_CORRECTED
MANUAL
```

正式数据来源必须从 ConfirmationItem 明确复制。

* * *

## 22.2 standard\_metric\_id 可空

对于：

```

KEEP_ORIGINAL_NAME
```

必须：

```

standard_metric_id = NULL
```

该数据可以：

*   出现在正式报告；
    
*   出现在普通历史查看中。
    

但 Stage 06 不得把它自动加入标准指标趋势聚合。

* * *

# 23\. 正式数据追溯

正式结果必须可追溯：

### OCR 自动采用

```

ReportAsset
→ OcrTask
→ OcrResultItem
→ ConfirmationItem(OCR_AUTO)
→ LabResult
```

### OCR 人工修正

```

ReportAsset
→ OcrResultItem：机器值
→ ConfirmationItem：用户最终确认值
→ LabResult：正式值
```

### 错误识别删除

```

OcrResultItem
→ ConfirmationItem.REMOVED
→ 无 LabResult
```

### 手工新增

```

ReportAsset
→ ConfirmationItem.MANUAL
→ LabResult
```

本阶段不得为了“数据简化”跳过 ConfirmationItem，直接让 LabResult 指向 OcrResultItem。

* * *

# 24\. API 范围

统一前缀：

```

/api/v1
```

具体响应格式遵循当前工程风格。

* * *

## 24.1 获取确认工作区

建议：

```

GET /api/v1/ingestions/{id}/confirmation
```

行为：

*   验证所有权；
    
*   ingestion 必须允许确认；
    
*   对 Stage 03 旧任务执行幂等 workspace 初始化；
    
*   返回报告级确认信息；
    
*   返回当前 HealthProfile；
    
*   返回原图基础信息；
    
*   返回 ConfirmationItem；
    
*   返回 pending review count；
    
*   返回 AUTO / REVIEW 来源信息；
    
*   返回必要的 source page / bbox 信息。
    

不得返回 COS 永久 URL。

* * *

## 24.2 修改报告信息

建议：

```

PATCH /api/v1/ingestions/{id}/confirmation
```

允许修改：

*   health\_profile\_id；
    
*   hospital\_name；
    
*   examination\_date；
    
*   examination\_time；
    
*   report\_no；
    
*   report\_category。
    

修改后必须保证重复检测 acknowledgement 不会错误沿用。

* * *

## 24.3 修改确认项

建议：

```

PATCH /api/v1/ingestions/{id}/confirmation/items/{item_id}
```

根据 body 支持：

*   确认正确；
    
*   修改字段；
    
*   选择 standard metric；
    
*   按原名称保存；
    
*   标记 REMOVED。
    

后端必须校验：

*   item 属于该 ingestion；
    
*   ingestion 属于当前用户；
    
*   当前状态允许编辑；
    
*   resolution 与字段组合合法。
    

不得物理删除 OCR 来源 ConfirmationItem。

* * *

## 24.4 手工新增

建议：

```

POST /api/v1/ingestions/{id}/confirmation/items
```

新增 MANUAL ConfirmationItem。

* * *

## 24.5 StandardMetric 查询

建议：

```

GET /api/v1/standard-metrics?q=
```

Stage 04 只读。

至少支持按：

*   code；
    
*   name
    

进行简单查询。

* * *

## 24.6 进入纯手工模式

可根据最终实现选择等价 API，例如：

```

POST /api/v1/ingestions/{id}/manual
```

要求：

*   当前用户拥有 ingestion；
    
*   至少一张有效原图；
    
*   只有合法状态允许进入；
    
*   不覆盖历史 OcrTask；
    
*   不删除原始资产；
    
*   最终进入 `PENDING_CONFIRMATION`。
    

* * *

## 24.7 commit

```

POST /api/v1/ingestions/{id}/commit
```

要求：

*   完整 commit validation；
    
*   重复提示；
    
*   用户明确继续重复保存；
    
*   单事务；
    
*   幂等；
    
*   返回正式 `report_id`。
    

成功后不要求 Stage 04 返回完整正式报告详情。

* * *

# 25\. 推荐稳定业务错误码

在现有约定基础上至少需要覆盖：

```

CONFIRMATION_NOT_READY
CONFIRMATION_SOURCE_INVALID
CONFIRMATION_ITEM_NOT_FOUND
CONFIRMATION_LOCKED
REVIEW_PENDING
INVALID_REPORT_DATE
INVALID_CONFIRMATION_ITEM
STANDARD_METRIC_NOT_FOUND
NO_REPORT_ITEMS
DUPLICATE_CONFIRM_REQUIRED
COMMIT_NOT_ALLOWED
```

最终错误码可结合现有项目风格收口。

前端必须依赖稳定 `code`，不得依赖中文 message 判断业务逻辑。

* * *

# 26\. 小程序 P0 页面

Stage 04 以业务正确为优先，不进行大规模 UI 精修。

## 26.1 P07｜识别结果确认页

新增确认页面。

当：

```

ReportIngestion = PENDING_CONFIRMATION
```

任务入口必须进入确认页，而不是继续停留在 OCR 状态页。

页面至少包含：

```

当前健康档案
报告基本信息
原始报告入口
待确认 REVIEW
已自动采用 AUTO
添加漏识别项目
最终确认并保存
```

* * *

## 26.2 REVIEW 优先展示

建议：

```

待确认 X 项
```

放在页面顶部。

REVIEW 必须有醒目标记。

AUTO 可以默认折叠或放在 REVIEW 下方，但必须可展开、可编辑。

* * *

## 26.3 指标编辑

可以使用独立指标编辑页或当前页面弹层。

至少支持：

*   指标名称；
    
*   结果；
    
*   单位；
    
*   参考范围；
    
*   标准指标；
    
*   查看来源原图；
    
*   按原名称保存；
    
*   删除错误识别。
    

避免为了 Stage 04 建设复杂通用表单系统。

* * *

## 26.4 原图核对

继续复用 Stage 03 已有短时 preview API。

OCR Item 已具备：

*   source asset；
    
*   page\_no；
    
*   bbox（可得时）。
    

Stage 04 P0 只要求：

```

查看对应页原图
```

不要求：

*   bbox 高亮框；
    
*   图片裁剪；
    
*   OCR 局部重识别；
    
*   高级图像标注。
    

* * *

## 26.5 手工新增

提供：

```

+ 添加漏识别项目
```

表单复用指标编辑能力。

* * *

## 26.6 纯手工报告

READY 或 OCR\_FAILED 的合法流程提供：

```

手工录入
```

进入相同 Confirmation 页面。

不建设第二套独立手工报告页面体系。

* * *

## 26.7 commit 成功页

成功后最小提示：

```

报告保存成功
X 项检验结果已保存
```

提供：

```

完成
```

返回首页或当前合理入口。

不得提前建设 Stage 05 正式报告详情。

* * *

# 27\. ingestion task 列表调整

现有 task 列表需要理解：

```

PENDING_CONFIRMATION
→ 打开 Confirmation 页面
```

对于：

```

CONFIRMED
```

Stage 04 不需要在 task 列表中建设正式报告查看能力。

可以：

*   显示“已保存”；
    
*   不提供打开正式报告详情；
    
*   或仅提供最小完成状态。
    

正式报告列表由 Stage 05 实现。

* * *

# 28\. 权限规则

Stage 04 所有写操作必须验证：

```

ReportIngestion.user_id == current_user.id
```

不能只根据 ConfirmationItem ID 修改。

必须通过关系确认：

```

ConfirmationItem
→ ReportIngestion
→ User
```

同样必须保护：

*   report-level confirmation；
    
*   item edit；
    
*   manual item add；
    
*   StandardMetric selection；
    
*   profile switch；
    
*   duplicate check；
    
*   commit。
    

HealthProfile 调整必须满足：

```

HealthProfile.user_id == current_user.id
HealthProfile.status == ACTIVE
```

* * *

# 29\. 异常与恢复

## 29.1 Confirmation 初始化失败

不得生成部分 workspace。

返回稳定错误。

允许用户稍后重新进入触发幂等初始化。

* * *

## 29.2 页面退出

Confirmation 所有已保存修改必须在服务端持久化。

流程：

```

修改 REVIEW
→ 离开页面
→ 关闭小程序
→ 再进入任务
```

必须恢复：

*   报告信息；
    
*   已 resolved 项；
    
*   AUTO 修改；
    
*   MANUAL 项；
    
*   REMOVED 项。
    

不得只保存在前端内存。

* * *

## 29.3 commit 失败

数据库事务失败：

*   ingestion 仍保持 PENDING\_CONFIRMATION；
    
*   不留下半份正式报告；
    
*   用户可以安全重试。
    

* * *

## 29.4 commit 成功但前端超时

用户重试 commit：

*   返回已有正式 LabReport；
    
*   不生成重复数据。
    

* * *

# 30\. 数据库 Migration

Stage 04 应新增独立 migration，建议：

```

0004_confirmation_report
```

不得重写：

```

0001
0002
0003
```

Migration 至少负责：

*   ReportIngestion 确认字段；
    
*   StandardMetric；
    
*   ConfirmationItem；
    
*   LabReport；
    
*   LabResult；
    
*   必要唯一约束；
    
*   外键；
    
*   索引。
    

必须验证：

```

现有 0003 数据库
→ upgrade head

以及

空 PostgreSQL
→ 0001
→ 0002
→ 0003
→ 0004
```

均成功。

* * *

# 31\. 测试要求

## 31.1 后端业务测试

至少覆盖：

### Confirmation 初始化

*   FINAL\_AUTO → RESOLVED；
    
*   FINAL\_REVIEW → PENDING；
    
*   初始化字段正确；
    
*   重复初始化幂等；
    
*   Stage 03 老 PENDING\_CONFIRMATION 任务可补初始化；
    
*   OcrResultItem 不变。
    

### REVIEW

覆盖：

*   ACCEPTED；
    
*   CORRECTED；
    
*   STANDARD\_METRIC\_SELECTED；
    
*   KEEP\_ORIGINAL\_NAME；
    
*   REMOVED。
    

### AUTO

*   默认采用；
    
*   用户主动修改；
    
*   修改后 source\_type 正确。
    

### MANUAL

*   漏识别新增；
    
*   手工项编辑；
    
*   纯手工报告；
    
*   OCR\_FAILED 转手工。
    

### Report info

*   日期校验；
    
*   HealthProfile 调整；
    
*   非本人 Profile 拒绝。
    

### StandardMetric

*   正常选择；
    
*   不存在 metric 拒绝；
    
*   未匹配允许按原名称保存；
    
*   不自动创建未知 StandardMetric。
    

### Duplicate

*   无重复正常 commit；
    
*   疑似重复返回提示；
    
*   用户明确继续后成功；
    
*   数据修改后旧 acknowledgement 失效。
    

### Commit

*   REVIEW pending 拒绝；
    
*   空报告拒绝；
    
*   缺日期拒绝；
    
*   正常生成 LabReport/LabResult；
    
*   REMOVED 不生成 LabResult；
    
*   standard\_metric NULL 正常保存；
    
*   单事务 rollback；
    
*   重复 commit 幂等；
    
*   并发 commit 只生成一份报告。
    

### 权限

User A 不得：

*   查看 B confirmation；
    
*   修改 B item；
    
*   添加 B item；
    
*   修改 B report info；
    
*   使用 B Profile；
    
*   commit B ingestion。
    

* * *

## 31.2 PostgreSQL 集成测试

事务和并发语义必须在真实 PostgreSQL 17 验证。

至少：

*   LabReport `source_ingestion_id` UNIQUE；
    
*   LabResult `source_confirmation_item_id` 唯一约束；
    
*   并发 commit；
    
*   rollback；
    
*   Stage 03 老数据 upgrade 后初始化。
    

不能只用 SQLite 证明 commit 并发安全。

* * *

## 31.3 前端

至少：

```

pnpm test（如当前 Stage 增加了可测试业务 helper）
pnpm typecheck
pnpm build:mp-weixin
```

并保持：

```

admin-web typecheck/build
```

不被破坏。

* * *

# 32\. 人工验收主流程

至少完成一份真实或脱敏格式报告：

```

Stage 03 PENDING_CONFIRMATION
↓
打开确认页
↓
查看原图
↓
填写/确认医院和检验日期
↓
确认 HealthProfile
↓
处理全部 REVIEW
↓
主动修改至少 1 条 AUTO
↓
手工新增至少 1 个漏识别项目
↓
至少验证一次标准指标选择
↓
至少验证一次按原名称保存
↓
疑似重复检查
↓
最终 commit
↓
LabReport 创建
↓
LabResult 正确创建
↓
ReportIngestion.CONFIRMED
```

人工确认：

*   OcrResultItem 未被修改；
    
*   原始图片仍存在；
    
*   正式值与 Confirmation 最终值一致；
    
*   未匹配标准指标项 standard\_metric\_id 为 NULL；
    
*   没有提前进入指标趋势。
    

* * *

# 33\. 本阶段明确不做

Stage 04 不得提前实现：

*   OCR 算法优化；
    
*   OCR threshold 调整；
    
*   OCR Pipeline 在线参数配置；
    
*   OCR bbox 高亮体验；
    
*   正式报告列表；
    
*   正式报告详情；
    
*   正式报告删除；
    
*   已保存报告档案迁移；
    
*   我的指标；
    
*   指标历史页面；
    
*   指标趋势；
    
*   关注指标；
    
*   Trend 表；
    
*   MetricFavorite；
    
*   MetricAlias 管理后台；
    
*   StandardMetric 管理后台；
    
*   管理员 OCR 排查页面；
    
*   医疗诊断；
    
*   AI 问诊；
    
*   医学解释；
    
*   健康评分；
    
*   跨单位复杂换算；
    
*   复杂 AuditLog/编辑版本系统。
    

* * *

# 34\. 最终交付物

Stage 04 完成后至少存在：

*   `0004_confirmation_report` 或等价 migration；
    
*   `StandardMetric`；
    
*   `ConfirmationItem`；
    
*   `LabReport`；
    
*   `LabResult`；
    
*   报告级确认字段；
    
*   Confirmation 初始化 service；
    
*   Confirmation API；
    
*   StandardMetric 查询 API；
    
*   手工录入入口；
    
*   duplicate detection；
    
*   transaction-safe commit；
    
*   idempotent commit；
    
*   小程序确认页面；
    
*   指标编辑能力；
    
*   手工新增能力；
    
*   commit 成功反馈；
    
*   后端自动测试；
    
*   PostgreSQL 并发/事务验证；
    
*   小程序 typecheck/build；
    
*   admin-web 回归构建；
    
*   `RESULT.md`。
    

* * *

# 35\. Definition of Done

只有同时满足：

```

Stage 03 PENDING_CONFIRMATION 老任务可直接进入确认
+
OcrResultItem 全程不可变
+
ConfirmationItem 幂等初始化
+
FINAL_AUTO 默认采用且可主动修改
+
FINAL_REVIEW 全部必须 resolved
+
REVIEW 五种处理方式可用
+
手工新增漏识别项目可用
+
纯手工报告兜底可用
+
报告级信息确认可用
+
HealthProfile 正式保存前可调整
+
StandardMetric 最小只读体系可用
+
未匹配指标可按原名称保存
+
疑似重复只提示、不阻断
+
commit validation 完整
+
commit 单事务
+
commit 幂等
+
LabReport / LabResult 正确生成
+
正式值可追溯到 ConfirmationItem / OcrResultItem / 原图
+
检验日期作为正式趋势时间来源
+
跨用户权限验证通过
+
ACCEPTANCE 全部 P0 PASS
+
自动测试、构建和真实人工主流程通过
+
RESULT.md 已更新
```

Stage 04 才可以标记为：

```

PASS
```

完成后停止，不进入 Stage 05 正式报告管理或 Stage 06 指标趋势。