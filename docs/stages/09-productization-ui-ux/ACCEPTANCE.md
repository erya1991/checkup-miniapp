# Stage 09｜整体产品化 + 统一 UI / UX 打磨｜ACCEPTANCE

**状态：FROZEN**

> 本文件是 Stage 09 唯一正式验收基线。
>
> P0 为阶段阻断项；所有适用 P0 必须 PASS，Stage 09 才能最终 PASS。
>
> P1 为推荐优化项，不得以实现 P1 为理由破坏 P0、扩大业务范围或进入 Stage 10。

---

# A. 基线与范围

- [ ] **A001 P0** 实施基线来自最新合法 `main`，开始前核对 `HEAD / origin/main / git status`。
- [ ] **A002 P0** Stage 00～08 RESULT 均保持 PASS，不篡改历史结论。
- [ ] **A003 P0** 按 `AGENTS.md` 顺序读取 Product / Tech / Development baseline、本 PLAN / ACCEPTANCE、Stage08 RESULT。
- [ ] **A004 P0** 实施前检查 Miniapp 当前全部真实页面与 Admin 当前真实页面，不按旧 baseline 臆造页面。
- [ ] **A005 P0** Stage 09 不进入 Stage 10、部署或发布。
- [ ] **A006 P0** 不修改已冻结 OCR runtime / matcher / threshold / scoring / retry / evidence。
- [ ] **A007 P0** 不修改 0001～0008 历史 migration。
- [ ] **A008 P0** 不顺手修复 Stage03 已知 ORM / migration index drift。

---

# B. Migration / 数据模型

- [ ] **B001 P0** Stage 09 新增 migration 数量 = 0。
- [ ] **B002 P0** migration head 仍为 `0008_profile_data_deletion`。
- [ ] **B003 P0** 不为首页、UI 状态、确认进度新增持久化字段。
- [ ] **B004 P0** 不新增健康评分、医学结论、风险评估相关字段。
- [ ] **B005 P0** 不新增独立 Trend 表或 UI Cache 表。
- [ ] **B006 P0** 若实施确实发现 schema P0 缺口，必须停止并重新确认范围，不能自行创建 0009。

---

# C. 一级信息架构 / Tab

- [ ] **C001 P0** Miniapp 正式存在三个一级 Tab：`首页 / 报告 / 我的`。
- [ ] **C002 P0** 不新增“指标”第四 Tab。
- [ ] **C003 P0** “我的指标”作为“报告”一级模块下的第二正式数据视角。
- [ ] **C004 P0** 一级 Tab 之间使用稳定 Tab 导航语义，不通过连续 `navigateTo` 模拟 Tab。
- [ ] **C005 P0** 从详情页返回一级模块路径自然，无明显返回循环。
- [ ] **C006 P0** Confirmation 保存成功后可进入正式报告，并可回到稳定一级页面。
- [ ] **C007 P0** 报告删除后回到报告模块，而不是残留已删除详情页。
- [ ] **C008 P0** 删除最后一个健康档案后，三个 Tab 均进入合法无档案状态。
- [ ] **C009 P1** Tab 图标和文字视觉统一，当前态明显但不过度装饰。

---

# D. 健康档案全局上下文

- [ ] **D001 P0** 首页清晰显示当前健康档案。
- [ ] **D002 P0** 报告 / 我的指标清晰显示当前健康档案。
- [ ] **D003 P0** “我的”存在健康档案管理入口。
- [ ] **D004 P0** 切换档案后首页数据切换。
- [ ] **D005 P0** 切换档案后报告数据切换。
- [ ] **D006 P0** 切换档案后我的指标数据切换。
- [ ] **D007 P0** 不同档案数据不得混合。
- [ ] **D008 P0** 旧请求晚返回不得覆盖新档案数据。
- [ ] **D009 P0** 页面不再普遍重复“当前档案 + 切换按钮”的工程式布局。
- [ ] **D010 P0** 无档案时可直接进入创建本人档案流程。

---

# E. 首页产品化

- [ ] **E001 P0** 首页不再是单纯功能按钮集合。
- [ ] **E002 P0** 首页第一层明确当前健康档案。
- [ ] **E003 P0** “上传检验报告”是首页最明显主动作。
- [ ] **E004 P0** 首页上传主动作明确表达“识别后仍需用户核对才能保存”。
- [ ] **E005 P0** 首页不平铺拍照 / 相册 / OCR / 手工录入多个等权主按钮。
- [ ] **E006 P0** 有未完成 ingestion 时显示待处理摘要。
- [ ] **E007 P0** 同时多份未完成任务时，不再只依赖单一 `draft` 概念。
- [ ] **E008 P0** 首页可进入全部待处理报告。
- [ ] **E009 P0** 待确认任务优先级高于识别中 / 普通上传未完成。
- [ ] **E010 P0** 首页最近报告只使用正式 LabReport 数据。
- [ ] **E011 P0** 最近报告显示检验日期；医院 / 分类存在时合理展示。
- [ ] **E012 P0** 最近报告异常数量只使用持久化正式 abnormal 汇总。
- [ ] **E013 P0** 首页不重新计算 abnormal。
- [ ] **E014 P0** 当前档案有 Favorite 时可展示少量关注指标摘要。
- [ ] **E015 P0** 关注指标摘要只显示正式 latest / unit / date / persisted abnormal。
- [ ] **E016 P0** 首页不生成健康评分、疾病风险、医学解释、趋势结论或建议。
- [ ] **E017 P0** 空档案 / 空报告 / 无 Favorite 时首页不出现无意义空卡片堆叠。

---

# F. 新上传 vs 继续任务

- [ ] **F001 P0** 点击“上传检验报告”明确进入新的报告上传流程。
- [ ] **F002 P0** 新上传入口不得意外打开 CONFIRMED ingestion。
- [ ] **F003 P0** 新上传入口不得随机复用旧未完成任务。
- [ ] **F004 P0** 已存在未完成任务时，用户通过“待处理报告 / 继续处理”明确选择对应 ingestion。
- [ ] **F005 P0** “继续上传”只作用于指定 UPLOADING / READY ingestion。
- [ ] **F006 P0** 多份未完成任务不会互相覆盖。
- [ ] **F007 P0** 上传页面所属健康档案清楚。
- [ ] **F008 P0** 原有多图上传 / 追加 / 排序 / 删除 / 重试能力保留。
- [ ] **F009 P0** 开始识别后图片与页序仍按冻结规则锁定。
- [ ] **F010 P0** 手工录入作为次级兜底动作，不取代正常 OCR 主流程。

---

# G. 待处理报告（原识别任务记录）

- [ ] **G001 P0** 普通用户页面产品名为“待处理报告”或语义等价名称，不再主称“识别任务记录”。
- [ ] **G002 P0** 只展示未完成 ingestion。
- [ ] **G003 P0** `UPLOADING` 显示用户可理解的上传未完成状态。
- [ ] **G004 P0** `READY` 显示待开始识别。
- [ ] **G005 P0** `QUEUED` 显示等待识别。
- [ ] **G006 P0** `PROCESSING` 显示正在识别。
- [ ] **G007 P0** `OCR_FAILED` 显示识别失败。
- [ ] **G008 P0** `PENDING_CONFIRMATION` 显示待确认。
- [ ] **G009 P0** 卡片可打开对应正确页面继续处理。
- [ ] **G010 P0** 不再把 OcrTask 初始 `auto_count / review_count` 表现为 Confirmation 当前进度。
- [ ] **G011 P0** 可以展示机器初始 `total_count`，但必须避免误导为当前待核对数量。
- [ ] **G012 P0** CONFIRMED 不出现在待处理列表。
- [ ] **G013 P0** 切换档案后待处理列表完全切换。

---

# H. OCR 状态页

- [ ] **H001 P0** QUEUED 用户文案清楚。
- [ ] **H002 P0** PROCESSING 用户文案清楚。
- [ ] **H003 P0** 页面明确说明识别期间可以离开、后台继续处理。
- [ ] **H004 P0** PENDING_CONFIRMATION 明确“识别完成，但报告尚未正式保存”。
- [ ] **H005 P0** PENDING_CONFIRMATION 主动作是“核对报告/核对结果”。
- [ ] **H006 P0** OCR_FAILED 提供重新识别。
- [ ] **H007 P0** OCR_FAILED 提供保留原图转手工录入。
- [ ] **H008 P0** 原始 error_code 不作为普通用户主信息。
- [ ] **H009 P0** 原图仍可查看。
- [ ] **H010 P0** retry / lease / Worker 业务逻辑未改。

---

# I. Confirmation 页面

- [ ] **I001 P0** 用户能明确看到流程处于“核对结果”，不是已完成正式保存。
- [ ] **I002 P0** 顶部或首屏能看到当前待核对项目数量。
- [ ] **I003 P0** 原始报告核对入口高可达。
- [ ] **I004 P0** 报告基本信息结构清晰。
- [ ] **I005 P0** 需要核对项目视觉优先于已采用项目。
- [ ] **I006 P0** REVIEW / PENDING 普通用户主文案为“需要核对”或等价语义。
- [ ] **I007 P0** AUTO 普通用户主文案为“已自动采用”或等价语义。
- [ ] **I008 P0** Miniapp 不要求用户理解 AUTO / REVIEW 枚举。
- [ ] **I009 P0** 已自动采用项仍可主动编辑。
- [ ] **I010 P0** REVIEW 仍必须 resolved 才允许 commit。
- [ ] **I011 P0** “关联指标”搜索和选择可用。
- [ ] **I012 P0** canonical name 是用户主展示；code 不作为必需理解内容。
- [ ] **I013 P0** “按报告原名称保存”入口清楚。
- [ ] **I014 P0** 按报告原名称保存时明确“不参与我的指标趋势”或等价说明。
- [ ] **I015 P0** KEEP_ORIGINAL_NAME 工程枚举不直接暴露给普通用户。
- [ ] **I016 P0** 手工补项入口保留。
- [ ] **I017 P0** 删除错误识别入口保留，并保留原 OCR 审计事实。
- [ ] **I018 P0** 已移除项目可弱化 / 折叠，但可重新核对。
- [ ] **I019 P0** 最终主 CTA 明确为“确认并保存报告”或等价语义。
- [ ] **I020 P0** 最终保存前仍校验报告检验日期。
- [ ] **I021 P0** REVIEW_PENDING 阻断继续有效。
- [ ] **I022 P0** 疑似重复报告确认继续有效。
- [ ] **I023 P0** commit 幂等 / 响应丢失恢复继续有效。
- [ ] **I024 P0** 退出重进 Confirmation 状态保持。
- [ ] **I025 P0** OcrResultItem 未被前端编辑覆盖。
- [ ] **I026 P1** 已采用 / 已移除区域在长报告中可折叠或使用等价降噪方式。
- [ ] **I027 P1** 最终主操作在长页面中保持较高可达性，例如 sticky 区域或明确底部操作区。

---

# J. 正式报告列表

- [ ] **J001 P0** 报告列表属于“报告”一级模块。
- [ ] **J002 P0** 报告 / 我的指标二级切换明显。
- [ ] **J003 P0** 报告卡主信息优先：检验日期、医院/分类、项目数、异常标记数。
- [ ] **J004 P0** 报告编号降为次级信息。
- [ ] **J005 P0** 未填写医院 / 分类时不产生大量“未填写”视觉噪音。
- [ ] **J006 P0** 列表排序继续使用服务端正式排序。
- [ ] **J007 P0** 空报告状态给出“上传报告”下一步动作。
- [ ] **J008 P0** loading / error / retry 状态完整。
- [ ] **J009 P0** abnormal_count 继续只读正式 LabResult.abnormal。

---

# K. 正式报告详情

- [ ] **K001 P0** 报告基本信息和结果列表层级清晰。
- [ ] **K002 P0** 正式结果主名称继续使用 `LabResult.metric_name`。
- [ ] **K003 P0** 主结果继续使用 `result_text`。
- [ ] **K004 P0** 单位继续优先 normalized、缺失时回退 original。
- [ ] **K005 P0** 参考范围属于单次结果。
- [ ] **K006 P0** abnormal=NULL 不错误展示为“正常”。
- [ ] **K007 P0** persisted HIGH / LOW / 其它异常标记可读但不过度警报化。
- [ ] **K008 P0** StandardMetric 只作为辅助身份展示。
- [ ] **K009 P0** `standard_metric_id=NULL` 结果可显示“按本报告名称保存 / 不参与同类趋势”弱提示。
- [ ] **K010 P0** 不因 Stage09 新 Alias 重写历史正式结果。
- [ ] **K011 P0** 原始报告入口高可达。
- [ ] **K012 P0** 迁移报告属于低频操作，不与主查看动作等权。
- [ ] **K013 P0** 删除报告属于危险操作，不使用普通主按钮视觉。
- [ ] **K014 P0** 迁移疑似重复提示继续有效。
- [ ] **K015 P0** 删除完整数据链与 COS cleanup 语义继续有效。

---

# L. 原始报告

- [ ] **L001 P0** 原图多页顺序正确。
- [ ] **L002 P0** 原图短时签名 URL 逻辑不变。
- [ ] **L003 P0** 单页加载失败可单独重试。
- [ ] **L004 P0** 整页 error 可重试。
- [ ] **L005 P0** 空图片状态可理解。
- [ ] **L006 P0** 点击图片可预览大图。
- [ ] **L007 P0** Stage09 不修改 COS 私有访问边界。

---

# M. 我的指标列表

- [ ] **M001 P0** 我的指标继续只聚合当前档案正式 LabResult 且 `standard_metric_id != NULL`。
- [ ] **M002 P0** 指标列表作为“报告”一级模块第二视角。
- [ ] **M003 P0** canonical name 是主展示。
- [ ] **M004 P0** code 不作为普通用户主视觉字段。
- [ ] **M005 P0** 卡片显示 latest result_text。
- [ ] **M006 P0** 卡片显示最新单位与检验日期。
- [ ] **M007 P0** persisted abnormal 可显示。
- [ ] **M008 P0** Favorite 状态清楚。
- [ ] **M009 P0** “未关注”不应在每张卡上制造主要视觉噪音。
- [ ] **M010 P0** Favorite 指标继续优先排序。
- [ ] **M011 P0** 空指标状态可理解并能回到报告。
- [ ] **M012 P0** 切档案后列表不闪回旧请求。

---

# N. 指标详情 / 历史 / 趋势

- [ ] **N001 P0** 最新正式结果清楚。
- [ ] **N002 P0** 参考范围显示本次结果自己的 reference_text。
- [ ] **N003 P0** history 保留同日多次检测。
- [ ] **N004 P0** history 保留多单位和非数值结果。
- [ ] **N005 P0** 普通趋势只绘可靠 numeric points。
- [ ] **N006 P0** 阈值 comparator / 非数值不被强行画成普通点。
- [ ] **N007 P0** 多单位仍分序列，不换算、不混线。
- [ ] **N008 P0** 多单位切换产品表达清晰。
- [ ] **N009 P0** 长趋势可横向浏览或等价方式完整查看。
- [ ] **N010 P0** 点选后显示该点真实 result_text / unit / date / reference / abnormal。
- [ ] **N011 P0** 点选后可进入对应正式报告。
- [ ] **N012 P0** 无可绘制点时显示正常空趋势状态，不报错。
- [ ] **N013 P0** 不新增趋势解释、医学结论、改善/恶化判断。
- [ ] **N014 P0** Favorite 开关继续档案级独立。
- [ ] **N015 P1** 日期标签密度优化，避免明显重叠难读。

---

# O. 健康档案管理

- [ ] **O001 P0** 当前档案状态明显。
- [ ] **O002 P0** 切换档案是高频动作，操作可达。
- [ ] **O003 P0** 编辑是普通管理动作。
- [ ] **O004 P0** 永久删除是低频危险动作，不与切换 / 编辑等权。
- [ ] **O005 P0** 删除前继续请求服务端 deletion-impact。
- [ ] **O006 P0** 删除确认文案明确不可恢复。
- [ ] **O007 P0** PROCESSING OCR 时删除继续阻断。
- [ ] **O008 P0** 默认档案删除后 replacement 规则不变。
- [ ] **O009 P0** 最后一个档案可删除。
- [ ] **O010 P0** 删除最后档案后可重新创建本人档案。
- [ ] **O011 P0** 服务端已删除但客户端丢失204时，刷新后能按服务端事实恢复。
- [ ] **O012 P0** 不重新设计 Stage08 数据删除链路。

---

# P. 新增 / 编辑档案

- [ ] **P001 P0** 表单字段与 Stage02 既有字段一致。
- [ ] **P002 P0** 必填 / 可选层级清楚。
- [ ] **P003 P0** 保存 loading 防重复点击。
- [ ] **P004 P0** 错误反馈清楚。
- [ ] **P005 P0** 不新增未经确认的健康资料字段。

---

# Q. “我的”Tab

- [ ] **Q001 P0** 存在“我的”一级 Tab 页面。
- [ ] **Q002 P0** 显示当前健康档案摘要。
- [ ] **Q003 P0** 有健康档案管理入口。
- [ ] **Q004 P0** 有简洁的数据与隐私说明或等价可达信息。
- [ ] **Q005 P0** 有产品使用边界说明：报告整理 / 趋势查看，不提供诊断、风险预测、用药建议。
- [ ] **Q006 P0** 不新增会员、消息中心、家人邀请、通知、分享等超范围功能。
- [ ] **Q007 P1** 可显示轻量版本信息，但不得产生复杂设置中心。

---

# R. Miniapp 视觉系统

- [ ] **R001 P0** 形成公共设计 token 或等价统一来源。
- [ ] **R002 P0** 页面背景色统一。
- [ ] **R003 P0** 主文字 / 次文字 / 弱文字颜色统一。
- [ ] **R004 P0** 品牌主色统一，整体不过度“强科技蓝”。
- [ ] **R005 P0** danger / warning / abnormal / success 有明确区分。
- [ ] **R006 P0** abnormal 不被设计成等价“严重危险警报”。
- [ ] **R007 P0** 标题 / section / 正文 / 辅助字号层级统一。
- [ ] **R008 P0** 页面水平边距统一。
- [ ] **R009 P0** 卡片圆角 / 边框 / 阴影规则统一。
- [ ] **R010 P0** 按钮高度与主次视觉统一。
- [ ] **R011 P0** 避免明显卡片套卡片。
- [ ] **R012 P0** 不大面积使用高饱和渐变和装饰背景。
- [ ] **R013 P0** 指标页与其它页的 px / rpx 使用不再明显割裂。
- [ ] **R014 P0** 微信系统字体放大后核心操作仍可见可操作。
- [ ] **R015 P1** 使用简洁一致的图标，不引入大体积仅为装饰的图标框架。

---

# S. Miniapp 统一交互状态

- [ ] **S001 P0** 所有主要数据页都有 loading。
- [ ] **S002 P0** 所有列表页都有 empty。
- [ ] **S003 P0** 所有主要数据页都有 error。
- [ ] **S004 P0** 可恢复错误有 retry。
- [ ] **S005 P0** 网络失败不会直接显示内部异常堆栈。
- [ ] **S006 P0** 页面错误不泄露 Secret / Token / COS key / OCR 全文。
- [ ] **S007 P0** 主操作使用统一 primary 视觉。
- [ ] **S008 P0** 次操作与主操作有明显层级。
- [ ] **S009 P0** danger 操作使用独立危险视觉。
- [ ] **S010 P0** Toast 用于轻量反馈。
- [ ] **S011 P0** Modal / ActionSheet 用于不可恢复或需要明确选择的操作。
- [ ] **S012 P0** 页面不再普遍出现多个原生默认按钮等权堆叠。
- [ ] **S013 P1** 高频页面可以使用 skeleton，但不作为强制，也不新增复杂依赖。

---

# T. 工程术语产品化

Miniapp 普通用户主界面：

- [ ] **T001 P0** 不直接用 `UPLOADING` 作为主状态文案。
- [ ] **T002 P0** 不直接用 `READY` 作为主状态文案。
- [ ] **T003 P0** 不直接用 `PENDING_CONFIRMATION` 作为主状态文案。
- [ ] **T004 P0** 不直接用 `AUTO / REVIEW` 作为必须理解的主文案。
- [ ] **T005 P0** 不直接用 `KEEP_ORIGINAL_NAME`。
- [ ] **T006 P0** 不直接用 `StandardMetric` 作为普通用户概念。
- [ ] **T007 P0** 不直接用 ingestion / task / run / pipeline 作为普通用户主术语。
- [ ] **T008 P0** 必要技术错误码只作为次级排错信息。

Admin Web 可保留上述工程术语。

---

# U. Admin Web 基础统一

- [ ] **U001 P0** Admin 登录页视觉与主后台一致。
- [ ] **U002 P0** Admin shell / header / aside 层级清楚。
- [ ] **U003 P0** 当前导航项明显。
- [ ] **U004 P0** 各页面标题与说明位置统一。
- [ ] **U005 P0** 搜索工具栏间距和控件宽度合理。
- [ ] **U006 P0** 表格 loading / empty / error 可用。
- [ ] **U007 P0** ACTIVE / INACTIVE / Task status 使用统一 Tag 或等价表达。
- [ ] **U008 P0** Dialog / Form 按钮主次统一。
- [ ] **U009 P0** 删除 / 停用等风险操作与普通编辑视觉区分。
- [ ] **U010 P0** 现有 StandardMetric / Alias / OCR Issue / OCR Task 功能保持。
- [ ] **U011 P0** 不新增 RBAC / AdminUser 数据模型。
- [ ] **U012 P0** 不新增用户正式健康数据管理页面。
- [ ] **U013 P0** 不新增 OCR 在线参数配置。
- [ ] **U014 P1** Admin 首页可优化成简洁功能导航，但不建设运营数据看板。

---

# V. 冻结业务回归

- [ ] **V001 P0** OcrResultItem 仍不可被人工编辑覆盖。
- [ ] **V002 P0** FINAL_REVIEW / Confirmation PENDING 仍必须人工处理。
- [ ] **V003 P0** MetricAlias 不进入 OCR matcher。
- [ ] **V004 P0** 新 Alias 不重算已初始化 Confirmation。
- [ ] **V005 P0** 新 Alias 不回填历史 LabResult.standard_metric_id。
- [ ] **V006 P0** StandardMetric rename 不重写历史 LabResult.metric_name。
- [ ] **V007 P0** StandardMetric inactive 不隐藏既有报告 / 指标 / trend / Favorite。
- [ ] **V008 P0** 报告迁移仍整份一致迁移。
- [ ] **V009 P0** 报告删除仍完整删除来源链并登记可靠 COS cleanup。
- [ ] **V010 P0** HealthProfile 删除仍完整执行 Stage08 语义。
- [ ] **V011 P0** 趋势仍使用检验日期 / 时间。
- [ ] **V012 P0** 同日多次仍全部保留。
- [ ] **V013 P0** 多单位仍不换算、不混线。
- [ ] **V014 P0** 非数值结果仍进入 history，不强行进入普通趋势。
- [ ] **V015 P0** abnormal 仍不由 Stage09 重新计算。
- [ ] **V016 P0** 原始报告仍是最终核对依据。

---

# W. Miniapp 自动测试

至少新增 / 调整测试覆盖：

- [ ] **W001 P0** Tab / route 基础映射。
- [ ] **W002 P0** 待处理状态 → 产品文案映射。
- [ ] **W003 P0** 多未完成任务首页优先级。
- [ ] **W004 P0** 新上传不会复用 CONFIRMED ingestion。
- [ ] **W005 P0** 指定继续任务进入对应 ingestion。
- [ ] **W006 P0** Confirmation pending / adopted / removed 分组继续正确。
- [ ] **W007 P0** KEEP_ORIGINAL_NAME 产品展示逻辑。
- [ ] **W008 P0** standard_metric_id=NULL 正式结果展示不参与趋势说明。
- [ ] **W009 P0** 档案切换 request guard / stale response 防护继续有效。
- [ ] **W010 P0** 首页只使用正式报告 / 正式指标数据形成正式摘要。
- [ ] **W011 P0** Miniapp 全量 tests 通过。
- [ ] **W012 P0** Miniapp typecheck 通过。
- [ ] **W013 P0** Miniapp `build:mp-weixin` 通过。

---

# X. Backend / PostgreSQL 回归

- [ ] **X001 P0** Backend 全量 pytest 通过。
- [ ] **X002 P0** Backend Ruff 通过。
- [ ] **X003 P0** 如新增只读展示 API，有对应权限 / 空状态 / 错误测试。
- [ ] **X004 P0** `alembic heads` 唯一 head 仍为 0008。
- [ ] **X005 P0** Stage03 queue PostgreSQL 专项继续通过。
- [ ] **X006 P0** Stage04 confirmation PostgreSQL 专项继续通过。
- [ ] **X007 P0** Stage05 reports PostgreSQL 专项继续通过。
- [ ] **X008 P0** Stage06 metrics PostgreSQL 专项继续通过。
- [ ] **X009 P0** Stage07 admin PostgreSQL 专项继续通过。
- [ ] **X010 P0** Stage08 profile deletion PostgreSQL 专项继续通过。
- [ ] **X011 P0** 所有临时测试库最终无残留。
- [ ] **X012 P0** Stage03 已知两项 index drift 未被 Stage09 顺手修改。

---

# Y. Admin 自动验证

- [ ] **Y001 P0** Admin tests 通过。
- [ ] **Y002 P0** Admin typecheck 通过。
- [ ] **Y003 P0** Admin build 通过。
- [ ] **Y004 P0** 既有 Admin 功能测试未被删除或弱化以制造通过。

---

# Z. 代码与文档质量

- [ ] **Z001 P0** `git diff --check` 通过。
- [ ] **Z002 P0** 未提交真实医疗报告 / OCR 全文 / Secret。
- [ ] **Z003 P0** 未新增不必要的大型 UI 依赖。
- [ ] **Z004 P0** 未为了统一样式重写无关后端业务。
- [ ] **Z005 P0** PLAN / ACCEPTANCE 保持冻结，不在实现时降低 P0。
- [ ] **Z006 P0** 实施完成后 `RESULT.md` 记录真实完成内容。
- [ ] **Z007 P0** RESULT 记录自动测试真实结果。
- [ ] **Z008 P0** RESULT 记录真实微信人工验收结果。
- [ ] **Z009 P0** RESULT 记录 Admin 人工验收结果。
- [ ] **Z010 P0** RESULT 记录设计偏差和已知非阻塞问题。

---

# AA. 负责人真实微信人工验收

以下由项目负责人在真实微信环境完成；自动测试不得替代。

## T01｜三 Tab 与导航

步骤：

```text
启动小程序
→ 首页
→ 报告
→ 我的
→ 报告列表进入详情
→ 查看原图
→ 返回
→ 我的指标
→ 指标详情
→ 返回报告一级模块
```

PASS：

- 三 Tab 清楚；
- 返回路径自然；
- 不出现明显重复页面栈 / 死循环；
- 不需要依靠页面内“假返回按钮”理解导航。

结果：`PENDING`

---

## T02｜健康档案全局切换

准备至少两个档案，例如本人 / 父亲。

步骤：

```text
本人 → 查看首页 / 报告 / 我的指标
→ 切换父亲
→ 再查看首页 / 报告 / 我的指标
→ 切回本人
```

PASS：

- 三处数据始终属于当前档案；
- 无旧数据闪回；
- 不同档案不混合。

结果：`PENDING`

---

## T03｜新上传与多待处理任务

步骤：

1. 当前档案已有正式报告；
2. 点击首页“上传检验报告”；
3. 确认进入新的上传流程，而不是旧 CONFIRMED ingestion；
4. 创建至少两份不同未完成任务；
5. 回首页；
6. 进入“待处理报告”；
7. 分别打开两份任务。

PASS：

- 新上传与继续任务语义完全区分；
- 多任务都能保留和正确打开；
- 不互相覆盖。

结果：`PENDING`

---

## T04｜上传 → OCR → 待确认阶段感

步骤：

```text
上传多页报告
→ 排序 / 预览
→ 开始识别
→ QUEUED / PROCESSING 期间离开再进入
→ PENDING_CONFIRMATION
```

PASS：

- 用户始终知道当前阶段；
- 识别中允许离开；
- “识别完成”明确不等于“正式报告已保存”；
- 原图仍可查看。

结果：`PENDING`

---

## T05｜Confirmation 产品化完整流程

使用包含至少 1 个需核对项的真实 / 合成安全报告。

步骤：

```text
进入确认页
→ 查看原图
→ 修改一个需要核对项目
→ 确认一个正确项目
→ 修改一个已自动采用项目
→ 选择标准指标
→ 按报告原名称保存一个项目
→ 手工补项
→ 退出重进
→ 最终确认并保存
```

PASS：

- 需要核对项目优先明确；
- AUTO / REVIEW 技术词不是理解流程的前提；
- 按原名称保存说明清楚“不进入我的指标趋势”；
- 退出重进状态不丢；
- REVIEW 未处理时仍阻止保存；
- 最终保存后生成正式报告。

结果：`PENDING`

---

## T06｜待处理报告统计债务复验

准备一份 OCR 初始存在 REVIEW 的任务并处理完全部 REVIEW，但在正式保存前观察待处理入口。

PASS：

- 待处理卡不再用旧 `auto_count / review_count` 冒充当前确认进度；
- 用户不会看到“明明已处理仍显示待核对2项”的误导；
- Confirmation 内真实 pending 数量正确。

结果：`PENDING`

---

## T07｜正式报告体验

步骤：

```text
报告列表
→ 报告详情
→ 查看异常标记
→ 查看按原名称保存项目
→ 查看原图
→ 迁移到另一档案并返回
→ 删除一份测试报告
```

PASS：

- 信息层级清楚；
- 异常只展示事实标记，无医学判断；
- 按原名称保存项目解释清楚；
- 迁移 / 删除是低频管理操作；
- 删除不可恢复提示清楚；
- 原图入口明显。

结果：`PENDING`

---

## T08｜我的指标 / 趋势

准备：

```text
Favorite 指标
≥3 个同单位 numeric 点
同一指标至少两种单位
至少 1 个非数值 / comparator 结果
```

步骤：

```text
报告 → 我的指标
→ Favorite
→ 指标详情
→ 切换单位
→ 点选趋势点
→ 查看完整历史
→ 从趋势 / 历史回到来源报告
```

PASS：

- latest / history / trend 信息可理解；
- 多单位不混线；
- 非数值仍在历史中；
- 无可绘制点时是正常空状态；
- 不出现医学解释或趋势好坏结论。

结果：`PENDING`

---

## T09｜首页摘要边界

准备当前档案同时具有：

```text
最近正式报告
abnormal 标记
Favorite
一份待处理任务
```

PASS：

- 首页正确展示待处理、最近报告、关注指标；
- abnormal 只做事实展示；
- 不出现健康评分 / 风险 / 建议；
- 主动作仍是上传报告。

结果：`PENDING`

---

## T10｜健康档案管理与永久删除 UI

步骤：

```text
新增档案
→ 编辑
→ 切换
→ 删除非默认档案
→ 删除当前默认档案
→ 删除最后一个档案
→ 重新创建本人档案
```

PASS：

- 切换 / 编辑 / 删除视觉层级合理；
- 删除影响摘要与不可恢复确认清楚；
- Stage08 删除行为保持；
- 最后一个档案删除后产品不崩溃，可重新创建。

结果：`PENDING`

---

## T11｜状态 / 空页 / 错误体验

至少覆盖：

```text
无健康档案
无正式报告
无指标
无趋势点
无待处理报告
网络错误后重试
OCR_FAILED
```

PASS：

- empty / error / retry 文案一致、可理解；
- 用户知道下一步做什么；
- 不暴露明显工程内部信息。

结果：`PENDING`

---

# AB. Admin Web 负责人真实人工验收

## T12｜Admin 基础一致性

步骤：

```text
登录
→ 首页
→ 标准指标列表 / 详情
→ 新增或编辑测试指标
→ Alias
→ OCR 指标问题
→ OCR Task
→ 制造一个普通查询空状态 / 可恢复错误
```

PASS：

- 导航和页面层级一致；
- 表格 / 搜索 / Dialog / loading / empty / error 清楚；
- ACTIVE / INACTIVE / Task status 可读；
- 原 Stage07 业务能力保持；
- 没有新增用户健康数据管理 / RBAC / OCR 在线调参。

结果：`PENDING`

---

# AC. Stage 09 最终自动验证命令

最终收尾至少执行并记录真实结果；具体命令以实施时最新 README / package / pyproject 为准：

```text
backend:
  .venv/Scripts/python.exe -m pytest -q ...
  .venv/Scripts/ruff.exe check . --no-cache
  .venv/Scripts/alembic.exe heads
  .venv/Scripts/python.exe tests/verify_postgres_queue.py
  .venv/Scripts/python.exe tests/verify_postgres_confirmation.py
  .venv/Scripts/python.exe tests/verify_postgres_reports.py
  .venv/Scripts/python.exe tests/verify_postgres_metrics.py
  .venv/Scripts/python.exe tests/verify_postgres_stage07.py
  .venv/Scripts/python.exe tests/verify_postgres_profile_deletion.py

miniapp:
  pnpm test
  pnpm typecheck
  pnpm build:mp-weixin

admin-web:
  pnpm test
  pnpm typecheck
  pnpm build

root:
  git diff --check
```

- [ ] **AC001 P0** 上述适用自动回归全部 PASS。
- [ ] **AC002 P0** 不删除 / skip / 弱化既有测试制造通过。
- [ ] **AC003 P0** 临时 PostgreSQL 测试库最终全部清理。
- [ ] **AC004 P0** 微信构建产物可导入微信开发者工具。

---

# AD. 安全阻断项

以下任一失败，Stage 09 不得 PASS：

- [ ] **AD001 P0** OcrResultItem immutable。
- [ ] **AD002 P0** REVIEW 不被 UI / Alias 自动提升为 AUTO / 已确认。
- [ ] **AD003 P0** 历史 LabResult 不回填 / 重标准化。
- [ ] **AD004 P0** abnormal 不重新计算。
- [ ] **AD005 P0** 趋势不做跨单位换算。
- [ ] **AD006 P0** 原始报告可追溯。
- [ ] **AD007 P0** HealthProfile 删除仍保护 PROCESSING OCR。
- [ ] **AD008 P0** 不新增医疗建议 / 风险 / 健康评分。
- [ ] **AD009 P0** 无新 migration。
- [ ] **AD010 P0** OCR runtime / Pipeline Version 未因 Stage09 改变。

---

# AE. 最终 PASS 条件

只有同时满足：

```text
A～AD 所有适用 P0 = PASS
+
Miniapp 自动测试 / typecheck / 微信 build = PASS
+
Admin 自动测试 / typecheck / build = PASS
+
Backend 全量回归 = PASS
+
Stage03～08 PostgreSQL 既有专项 = PASS
+
负责人真实微信 T01～T11 = PASS
+
负责人 Admin T12 = PASS
+
0 migration
+
冻结数据语义未改变
+
RESULT.md 已完成
```

才能：

```text
Stage 09 = PASS
```

人工验收未完成前，RESULT 最多可标记：

```text
AUTOMATED PASS / WAITING MANUAL ACCEPTANCE
```

不得提前宣称 Stage 09 最终 PASS。

---

# AF. 最终 RESULT 建议结构

```text
Stage 09：PASS / FAIL

1. 实际完成范围
2. 信息架构与页面变更
3. UI / UX Design System 落地
4. 历史体验债务收口
5. 0 migration / 冻结边界核验
6. Backend 自动回归
7. PostgreSQL 17 回归
8. Miniapp tests / typecheck / build
9. Admin tests / typecheck / build
10. 负责人真实微信 T01～T11
11. Admin T12
12. 设计偏差
13. 已知非阻塞问题
14. Git / commit / push / main 引用
15. 最终结论
```
