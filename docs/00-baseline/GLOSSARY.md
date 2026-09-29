# GLOSSARY｜项目术语表

| 术语 | 含义 |
|---|---|
| User | 一个微信身份对应的系统用户 |
| HealthProfile | 用户管理的本人/父母/其他家庭成员健康档案 |
| ReportIngestion | 一次“上传→OCR→人工确认→提交”的临时导入工作区 |
| ReportAsset | 导入任务中的原始报告图片 |
| OcrTask | 一次独立 OCR Pipeline 执行任务，可重试并产生多个 run |
| OcrResultItem | OCR Pipeline 某一次 run 的结构化行快照，不允许人工覆盖 |
| ConfirmationItem | 用户确认工作区中的可编辑检验项目 |
| FINAL_AUTO | OCR Pipeline 已达到允许默认采用条件的项目，仍需整份报告最终 commit |
| FINAL_REVIEW | 必须由用户显式处理后才能 commit 的项目 |
| RESOLVED | REVIEW 已通过确认/校正/按原名保存/删除等方式完成处理 |
| KEEP_ORIGINAL_NAME | 无法/无需映射标准指标，按原名称进入正式报告，不进入标准指标趋势 |
| LabReport | 用户 commit 后形成的正式检验报告 |
| LabResult | 正式报告中的单条正式检验结果 |
| StandardMetric | 跨医院/跨时间聚合使用的标准指标身份 |
| MetricAlias | 医院原名称、简称、英文缩写、OCR 常见变体到 StandardMetric 的映射 |
| ReportCategory | 报告分类，仅用于管理/展示，不作为指标保存的硬前置 |
| MetricFavorite | 某健康档案对某 StandardMetric 的关注状态 |
| Original Report | 用户原始上传图片，是最终核对依据 |
| OCR Artifact | raw OCR/layout/rows/matched/final 等长期审计或回归产物 |
| Commit | 将全部已处理确认数据事务性生成 LabReport/LabResult 的正式保存动作 |
| Trend Series | 同一健康档案、标准指标、兼容标准化单位下的可绘图数值序列 |
| PoC | 已完成的 OCR 技术验证/Regression 工程，不等于正式产品工程 |
