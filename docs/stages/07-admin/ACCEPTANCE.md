# Stage 07｜StandardMetric / MetricAlias 管理与 OCR 轻量管理能力｜ACCEPTANCE

> 状态：**FROZEN / 待实施**
>
> 本文是 Stage 07 的唯一正式验收基线。  
> 实施必须同时遵循：
>
> ```text
> AGENTS.md
> docs/stages/07-admin/PLAN.md
> docs/stages/07-admin/ACCEPTANCE.md
> ```
>
> 本阶段只有在所有 P0 验收项通过、自动回归通过、PostgreSQL 17 专项通过、负责人真实人工验收通过后，才可标记 PASS。
>
> Stage 07 基线：
>
> ```text
> Stage 00～06 = PASS
> main baseline =
> b2b60f3854b66e5d04ad99568849f42e5844ce27
> ```

---

# 1. 验收原则

Stage 07 的验收重点不是页面数量，而是以下边界全部成立：

```text
产品 StandardMetric 主数据可持续维护
+
MetricAlias 可安全维护
+
Alias 只参与产品侧 exact resolution
+
REVIEW 安全边界不改变
+
既往 Confirmation / LabResult 不重算
+
Stage 06 历史与趋势不因主数据维护丢失
+
OCR runtime / matcher 不被本阶段修改
+
Admin 只能管理主数据和轻量排查
```

任何一项核心安全边界失败：

```text
Stage 07 = FAIL
```

---

# 2. P0 阻断项

以下属于 Stage 07 P0，任何一项失败都不能 PASS：

- [ ] P001 StandardMetric 可新增。
- [ ] P002 StandardMetric.code 创建后不可修改。
- [ ] P003 StandardMetric 可修改 name。
- [ ] P004 StandardMetric 可修改轻量 category。
- [ ] P005 StandardMetric 可停用。
- [ ] P006 StandardMetric 可恢复。
- [ ] P007 不提供 StandardMetric 物理删除能力。
- [ ] P008 未完成 Confirmation 正在引用 StandardMetric 时，停用必须被阻止。
- [ ] P009 已有正式 LabResult 引用不阻止 StandardMetric 停用。
- [ ] P010 INACTIVE StandardMetric 的既有 Stage 06 历史 / trend / favorite 继续可见。
- [ ] P011 MetricAlias 正式落库。
- [ ] P012 MetricAlias 只能归属一个 StandardMetric。
- [ ] P013 MetricAlias.active normalized_alias 全局唯一。
- [ ] P014 Alias 与其它 ACTIVE StandardMetric code/name 冲突时必须拒绝。
- [ ] P015 Alias 不进入冻结 OCR matcher。
- [ ] P016 Alias 不改变 FINAL_AUTO / FINAL_REVIEW。
- [ ] P017 Alias 命中 REVIEW 项时仍保持 PENDING_CONFIRMATION。
- [ ] P018 已存在 ConfirmationItem 不因新增 Alias 自动变化。
- [ ] P019 已存在 LabResult 不因新增 Alias 自动变化。
- [ ] P020 不批量回填历史 LabResult.standard_metric_id。
- [ ] P021 OcrResultItem 全程不可变。
- [ ] P022 Stage 04 标准指标搜索可通过 Alias 找到 canonical StandardMetric。
- [ ] P023 Product Exact Metric Resolver 仅使用 exact 规则。
- [ ] P024 OCR code exact 优先于 name / Alias exact。
- [ ] P025 OCR 未匹配名称可进入 Admin 待处理列表。
- [ ] P026 OCR 已识别 code 但产品 StandardMetric 缺失可进入 Admin 待处理列表。
- [ ] P027 OCR code 对应 INACTIVE StandardMetric 可进入 Admin 提醒列表。
- [ ] P028 OCR issue 统计不因 OCR retry 重复计算同一 ingestion 的旧成功 run。
- [ ] P029 Admin 可从未匹配名称创建 Alias。
- [ ] P030 Admin 可从产品缺失 OCR code 创建 StandardMetric。
- [ ] P031 Admin 使用独立管理员认证。
- [ ] P032 普通用户 JWT 不能访问 `/api/v1/admin/*`。
- [ ] P033 Admin JWT 不能伪装普通用户访问 HealthProfile / Report 正式用户数据接口。
- [ ] P034 OCR Task Admin 为只读，不允许改状态 / 强制成功 / 重跑 / 修改 OCR 结果。
- [ ] P035 `backend/ocr_runtime` 不因 Stage 07 改动。
- [ ] P036 OCR Pipeline Version 不因 Stage 07 改动。
- [ ] P037 Stage 03 已知 ORM / migration 漂移未被顺手修复。
- [ ] P038 新增独立 0007 migration，不修改 0001～0006。
- [ ] P039 PostgreSQL 17 migration 与唯一约束真实验证通过。
- [ ] P040 Stage 04 / 05 / 06 既有主流程完整回归通过。

---

# 3. StandardMetric 模型与数据库

## 3.1 Schema

- [ ] SM001 `standard_metrics` 保留现有 `id`。
- [ ] SM002 `standard_metrics` 保留现有 `code`。
- [ ] SM003 `standard_metrics` 保留现有 `name`。
- [ ] SM004 `standard_metrics` 新增可空 `category`。
- [ ] SM005 `standard_metrics` 保留 `status`。
- [ ] SM006 `created_at` / `updated_at` 正常维护。
- [ ] SM007 Stage 07 不新增参考范围字段。
- [ ] SM008 Stage 07 不新增单位换算字段。
- [ ] SM009 Stage 07 不新增 OCR 阈值 / fuzzy 参数字段。
- [ ] SM010 Stage 07 不新增独立 MetricCategory 复杂表。

## 3.2 code

- [ ] SM011 创建 StandardMetric 时 code 必填。
- [ ] SM012 code 去除首尾空格。
- [ ] SM013 code 全局唯一。
- [ ] SM014 重复 code 返回稳定业务错误。
- [ ] SM015 创建后 PATCH code 被明确拒绝，而不是静默忽略。
- [ ] SM016 StandardMetric rename 不改变 code。
- [ ] SM017 StandardMetric deactivate/reactivate 不改变 code。
- [ ] SM018 错误 code 的修正方式为停用旧项 + 新建新项，不支持 code rename。

## 3.3 name / category / status

- [ ] SM019 name 必填且不能为空字符串。
- [ ] SM020 name 可修改。
- [ ] SM021 category 可空。
- [ ] SM022 category 可修改。
- [ ] SM023 category 不参与核心 identity 判断。
- [ ] SM024 ACTIVE StandardMetric 可用于未来手工选择。
- [ ] SM025 INACTIVE StandardMetric 不再出现在新的普通用户标准指标选择结果中。
- [ ] SM026 INACTIVE StandardMetric 不参与未来 Product Exact Resolver。
- [ ] SM027 INACTIVE StandardMetric 不允许作为新 ACTIVE Alias 的目标。
- [ ] SM028 StandardMetric 不提供物理删除 API。

---

# 4. StandardMetric 停用安全

- [ ] SD001 无待确认引用时，ACTIVE → INACTIVE 成功。
- [ ] SD002 INACTIVE → ACTIVE 恢复成功。
- [ ] SD003 已有正式 LabResult 引用不阻止停用。
- [ ] SD004 已 CONFIRMED 的旧 ConfirmationItem 不阻止停用。
- [ ] SD005 存在未完成 `PENDING_CONFIRMATION` 工作区引用时停用失败。
- [ ] SD006 停用失败返回稳定错误码。
- [ ] SD007 错误详情可包含最小 pending reference count，但不得暴露不必要医疗数据。
- [ ] SD008 停用检查与状态修改在事务内完成。
- [ ] SD009 并发 commit / deactivate 不造成静默错误。
- [ ] SD010 极端并发下允许一个事务先成功，另一个得到稳定业务错误。
- [ ] SD011 不允许为了停用便利而取消 Stage 04 commit 的 ACTIVE 校验。

---

# 5. MetricAlias 模型

## 5.1 Schema

- [ ] MA001 新增 `metric_aliases` 表。
- [ ] MA002 包含主键 id。
- [ ] MA003 包含 `standard_metric_id` 外键。
- [ ] MA004 包含原始 `alias`。
- [ ] MA005 包含 `normalized_alias`。
- [ ] MA006 包含 `alias_type`。
- [ ] MA007 包含 `status`。
- [ ] MA008 包含 `created_at` / `updated_at`。
- [ ] MA009 一个 Alias 只能指向一个 StandardMetric。
- [ ] MA010 不支持 Alias → Alias。
- [ ] MA011 不支持一个 Alias 多目标。
- [ ] MA012 不提供 MetricAlias 物理删除 API。

## 5.2 alias_type

- [ ] MA013 支持 `SYNONYM`。
- [ ] MA014 支持 `ABBREVIATION`。
- [ ] MA015 支持 `OCR_VARIANT`。
- [ ] MA016 支持 `HOSPITAL_NAME`。
- [ ] MA017 alias_type 仅用于管理元数据。
- [ ] MA018 alias_type 不参与 OCR score。
- [ ] MA019 alias_type 不影响 REVIEW / AUTO 判定。

---

# 6. Alias normalization 与冲突

- [ ] AN001 Alias 创建时保存原始 alias。
- [ ] AN002 同时生成 normalized_alias。
- [ ] AN003 normalization 使用确定性规则。
- [ ] AN004 Unicode NFKC 行为有自动测试。
- [ ] AN005 首尾空格不影响 exact identity。
- [ ] AN006 前导 `*` / `＊` 按冻结规则处理。
- [ ] AN007 Γ / ɣ / γ 兼容规则与产品 normalization 一致。
- [ ] AN008 大小写差异不能创建冲突 Alias。
- [ ] AN009 约定的简单空格 / 分隔符差异不能绕过唯一约束。
- [ ] AN010 ACTIVE normalized_alias 全局唯一。
- [ ] AN011 相同 normalized Alias 指向同一 metric 也不允许重复创建。
- [ ] AN012 相同 normalized Alias 指向不同 metric 必须拒绝。
- [ ] AN013 Alias 与其它 ACTIVE StandardMetric.code normalized 冲突必须拒绝。
- [ ] AN014 Alias 与其它 ACTIVE StandardMetric.name normalized 冲突必须拒绝。
- [ ] AN015 Alias 与自身 StandardMetric code/name 等价时也拒绝冗余 Alias。
- [ ] AN016 INACTIVE Alias 不参与未来 resolver。
- [ ] AN017 INACTIVE Alias 不参与普通用户标准指标搜索。
- [ ] AN018 恢复 Alias 时重新执行完整冲突检查。
- [ ] AN019 并发创建相同 ACTIVE normalized_alias 只能成功一个。
- [ ] AN020 PostgreSQL 17 层具备可靠并发唯一保护，不只依赖 Python 先查后写。

---

# 7. StandardMetric namespace 冲突

- [ ] NS001 创建 StandardMetric 时检查 code 与 ACTIVE Alias 冲突。
- [ ] NS002 创建 StandardMetric 时检查 name 与 ACTIVE Alias 冲突。
- [ ] NS003 修改 StandardMetric.name 时检查 ACTIVE Alias 冲突。
- [ ] NS004 恢复 StandardMetric ACTIVE 时重新检查 namespace 冲突。
- [ ] NS005 namespace normalization 与 MetricAlias 使用同一实现。
- [ ] NS006 不在多个 API 中复制不同 normalization 规则。

---

# 8. MetricAlias 管理行为

- [ ] MB001 可为 ACTIVE StandardMetric 创建 Alias。
- [ ] MB002 不能为 INACTIVE StandardMetric 创建 ACTIVE Alias。
- [ ] MB003 Alias 可编辑原始 alias。
- [ ] MB004 Alias 可编辑 alias_type。
- [ ] MB005 Alias 可停用。
- [ ] MB006 Alias 可恢复。
- [ ] MB007 `standard_metric_id` 创建后只读。
- [ ] MB008 映射目标错误时采用停用旧 Alias + 新建 Alias。
- [ ] MB009 Alias 编辑重新计算 normalized_alias。
- [ ] MB010 Alias 编辑重新执行唯一性 / namespace 冲突检查。
- [ ] MB011 Alias 操作不修改 OcrResultItem。
- [ ] MB012 Alias 操作不修改既有 ConfirmationItem。
- [ ] MB013 Alias 操作不修改既有 LabResult。

---

# 9. Stage 04 StandardMetric 搜索增强

- [ ] SS001 原 `/api/v1/standard-metrics?q=` 保持兼容。
- [ ] SS002 code 搜索继续有效。
- [ ] SS003 name 搜索继续有效。
- [ ] SS004 ACTIVE Alias 搜索有效。
- [ ] SS005 Alias 搜索最终返回 canonical StandardMetric。
- [ ] SS006 不把 MetricAlias 作为业务 identity 返回给小程序。
- [ ] SS007 同一 StandardMetric 被多个 Alias 命中时结果去重。
- [ ] SS008 INACTIVE StandardMetric 不作为新选择结果。
- [ ] SS009 INACTIVE Alias 不参与搜索。
- [ ] SS010 现有确认页无需大规模改造即可消费响应。

---

# 10. Product Exact Metric Resolver

## 10.1 调用边界

- [ ] ER001 Resolver 只在 Confirmation workspace 首次初始化调用。
- [ ] ER002 已存在 ConfirmationItem 时再次进入确认页不重新 resolver。
- [ ] ER003 新增 Alias 后不重算已经初始化的 workspace。
- [ ] ER004 新增 StandardMetric 后不重算已经初始化的 workspace。

## 10.2 匹配顺序

- [ ] ER005 第一优先级：`OcrResultItem.standard_metric_code` exact → ACTIVE StandardMetric.code。
- [ ] ER006 OCR code 已有效命中时，不再被 name / Alias 改绑到其它 metric。
- [ ] ER007 OCR code 未命中时，可用 raw_metric normalized exact → ACTIVE StandardMetric.name/code。
- [ ] ER008 前述未命中时，可用 raw_metric normalized exact → ACTIVE MetricAlias.normalized_alias。
- [ ] ER009 全部未命中时 `standard_metric_id = NULL`。
- [ ] ER010 Resolver 不使用 fuzzy score。
- [ ] ER011 Resolver 不使用相似度阈值。
- [ ] ER012 Resolver 不使用 result 值推断。
- [ ] ER013 Resolver 不使用 reference range 推断。
- [ ] ER014 Resolver 不使用单位推断目标指标。
- [ ] ER015 Resolver 不修改 OcrResultItem.standard_metric_code。
- [ ] ER016 Resolver 不修改 OcrResultItem.standard_metric_name。

---

# 11. AUTO / REVIEW 安全边界

- [ ] RV001 Stage 07 不改 `OcrResultItem.final_decision`。
- [ ] RV002 原 FINAL_REVIEW + Alias exact 命中时可以预填 standard_metric_id。
- [ ] RV003 上述 REVIEW 项仍保持待用户确认。
- [ ] RV004 Alias 不允许 REVIEW → AUTO。
- [ ] RV005 Alias 不允许 PENDING → RESOLVED。
- [ ] RV006 原有 OCR code exact 的 FINAL_AUTO 行为继续兼容 Stage 04。
- [ ] RV007 若出现 FINAL_AUTO + 无可靠 OCR code 的异常组合，不得通过 Alias 静默提升为安全 AUTO。
- [ ] RV008 KEEP_ORIGINAL_NAME 用户显式选择优先于任何 Alias。
- [ ] RV009 commit 阶段不重新运行 Alias resolver。
- [ ] RV010 手工补项不因 metric_name 文本碰巧命中 Alias 而自动绑定，除非用户显式选择 canonical StandardMetric。

---

# 12. Alias 生效时间

- [ ] ET001 OCR 已完成、Confirmation 尚未初始化，新 Alias 可以影响首次初始化。
- [ ] ET002 Confirmation 已初始化，新 Alias 不改变当前 workspace。
- [ ] ET003 报告已 commit，新 Alias 不改变 LabResult。
- [ ] ET004 Alias 停用同样不反向改变既有 Confirmation / LabResult。
- [ ] ET005 Alias 恢复只影响未来首次初始化与搜索。

---

# 13. 历史数据保护

- [ ] HD001 Migration 不回填历史 `lab_results.standard_metric_id`。
- [ ] HD002 Migration 不重写历史 `confirmation_items.standard_metric_id`。
- [ ] HD003 Migration 不重写 `ocr_result_items.standard_metric_code`。
- [ ] HD004 Admin API 不提供历史 LabResult 批量重关联。
- [ ] HD005 Admin UI 不提供历史报告“重新标准化”按钮。
- [ ] HD006 既有 NULL standard_metric_id LabResult 继续保持 NULL。
- [ ] HD007 新 Alias 即使 exact 命中历史 metric_name，也不自动修复历史。
- [ ] HD008 Stage 07 不新增后台正式 LabResult 编辑入口。

---

# 14. StandardMetric rename 后的显示

- [ ] RN001 修改 StandardMetric.name 不修改历史 LabResult.metric_name。
- [ ] RN002 修改 StandardMetric.name 不修改历史 OcrResultItem.standard_metric_name。
- [ ] RN003 修改 StandardMetric.name 不修改既有 ConfirmationItem.metric_name。
- [ ] RN004 Stage 06 “我的指标”使用当前 StandardMetric.name。
- [ ] RN005 Stage 06 metric detail identity 使用当前 StandardMetric.name/code。
- [ ] RN006 history/trend 聚合仍按 StandardMetric.id，不因 rename 分裂。
- [ ] RN007 正式报告主项目名称仍显示持久化 `LabResult.metric_name`。
- [ ] RN008 正式报告如展示“标准指标”辅助信息，可显示当前 canonical StandardMetric.name/code。

---

# 15. StandardMetric inactive 后的历史行为

- [ ] IA001 已有正式 LabResult 的 INACTIVE StandardMetric 仍出现在“我的指标”。
- [ ] IA002 latest 仍可查询。
- [ ] IA003 history 仍可查询。
- [ ] IA004 trend 仍可查询。
- [ ] IA005 MetricFavorite 不因停用自动删除。
- [ ] IA006 普通用户侧不强制显示“指标已停用”警告。
- [ ] IA007 Stage 06 查询不得新增 `StandardMetric.status = ACTIVE` 历史过滤条件。

---

# 16. OCR Issue｜UNMATCHED_NAME

- [ ] OI001 raw_metric 非空且 `standard_metric_code IS NULL` 可进入未匹配候选。
- [ ] OI002 按 normalized raw_metric 聚合。
- [ ] OI003 返回 representative_name。
- [ ] OI004 返回 normalized_name。
- [ ] OI005 返回 occurrence_count。
- [ ] OI006 返回 ingestion_count。
- [ ] OI007 返回 latest_seen_at。
- [ ] OI008 可返回少量 sample_names。
- [ ] OI009 默认不返回 result_text。
- [ ] OI010 默认不返回 reference。
- [ ] OI011 默认不返回完整 OCR payload。
- [ ] OI012 默认不返回患者 / 健康档案敏感显示数据。
- [ ] OI013 Admin 可从该项发起创建 Alias。
- [ ] OI014 创建 Alias 后，不修改历史 OcrResultItem。
- [ ] OI015 当前 ACTIVE Alias 已覆盖该 normalized name 后，默认不再作为 pending unmatched 显示。

---

# 17. OCR Issue｜PRODUCT_METRIC_MISSING

- [ ] PM001 `standard_metric_code IS NOT NULL` 且产品不存在 ACTIVE 同 code 时可识别缺口。
- [ ] PM002 返回 OCR code。
- [ ] PM003 返回 OCR standard name（如快照存在）。
- [ ] PM004 返回 occurrence_count。
- [ ] PM005 返回 ingestion_count。
- [ ] PM006 返回 latest_seen_at。
- [ ] PM007 Admin 可从问题创建 StandardMetric。
- [ ] PM008 创建表单可预填 OCR code。
- [ ] PM009 创建表单可预填 OCR standard name。
- [ ] PM010 最终创建必须由管理员确认。
- [ ] PM011 不自动导入全部 PoC metric library。
- [ ] PM012 创建 StandardMetric 后既往 OcrResultItem 不修改。
- [ ] PM013 创建 StandardMetric 后既往已初始化 Confirmation 不重算。

---

# 18. OCR Issue｜PRODUCT_METRIC_INACTIVE

- [ ] PI001 OCR code 对应现有 INACTIVE StandardMetric 时可在 Admin 识别。
- [ ] PI002 Admin 可查看该提醒。
- [ ] PI003 Admin 可从 StandardMetric 管理正常恢复。
- [ ] PI004 系统不得自动把该 code 改绑到其它 StandardMetric。
- [ ] PI005 不修改历史 OcrResultItem。

---

# 19. OCR Issue 统计口径

- [ ] IS001 同一 ingestion 存在多个 OcrTask 时不会简单累加所有历史 run。
- [ ] IS002 只选择每个 ingestion 最新成功 OCR run，或实现等价稳定语义。
- [ ] IS003 failed run 不作为正常 metric issue 统计来源。
- [ ] IS004 retry 后旧成功 run 不造成双重计数。
- [ ] IS005 issue 状态基于当前 StandardMetric / Alias 动态计算即可。
- [ ] IS006 Stage 07 默认不新增独立 `OcrMetricIssue` 持久化表。
- [ ] IS007 若实现确需改变为持久化 issue 模型，必须先停下报告，不得自行扩大范围。

---

# 20. OCR Task Admin

- [ ] OT001 Admin 可查看 OCR Task 列表。
- [ ] OT002 至少显示 task id。
- [ ] OT003 至少显示 ingestion id。
- [ ] OT004 至少显示 run_no。
- [ ] OT005 至少显示 status。
- [ ] OT006 至少显示 pipeline_version。
- [ ] OT007 至少显示 attempt_count。
- [ ] OT008 至少显示 created / started / finished 时间中的已有字段。
- [ ] OT009 可显示 last_error_code。
- [ ] OT010 可显示 result_summary 的轻量数量摘要。
- [ ] OT011 可按 status 筛选。
- [ ] OT012 可按 pipeline_version 筛选。
- [ ] OT013 不提供重新执行按钮。
- [ ] OT014 不提供强制成功按钮。
- [ ] OT015 不提供状态编辑。
- [ ] OT016 不提供 attempt / lease 编辑。
- [ ] OT017 不提供 OcrResultItem 编辑。
- [ ] OT018 不提供 OCR threshold 配置。
- [ ] OT019 不提供 Pipeline version 在线修改。

---

# 21. Admin Auth

## 21.1 登录

- [ ] AU001 Admin Web 有独立登录页。
- [ ] AU002 管理员凭据来自安全环境配置。
- [ ] AU003 Git 中没有真实管理员密码。
- [ ] AU004 Git 中没有真实 Admin JWT secret。
- [ ] AU005 密码以安全 hash 校验，不以明文数据库 / 代码比较。
- [ ] AU006 登录成功返回 Admin scoped token。
- [ ] AU007 登录失败返回稳定错误，不泄露密码。
- [ ] AU008 登录失败日志不包含原始密码。

## 21.2 权限隔离

- [ ] AU009 无 Admin token 调用 `/api/v1/admin/*` 返回 401/稳定错误。
- [ ] AU010 普通微信用户 token 调用 Admin API 被拒绝。
- [ ] AU011 Admin token 调用普通用户专属 HealthProfile 数据接口不能被当作普通用户身份接受。
- [ ] AU012 Admin token 与普通用户 token 的 scope / claim / secret 或等价安全边界清晰。
- [ ] AU013 Stage 07 不新增 AdminUser / Role / Permission / RBAC 复杂模型。
- [ ] AU014 Admin Auth 失败不会影响普通微信用户登录。

---

# 22. Admin API

- [ ] AA001 Admin API 统一位于 `/api/v1/admin/*`。
- [ ] AA002 StandardMetric list API 可搜索。
- [ ] AA003 StandardMetric list API 可按 status 筛选。
- [ ] AA004 StandardMetric list API 可按 category 筛选。
- [ ] AA005 StandardMetric list 有分页或当前规模下等价安全限制。
- [ ] AA006 StandardMetric list 可提供 alias_count。
- [ ] AA007 StandardMetric list 可提供 formal_result_count。
- [ ] AA008 StandardMetric list 可提供 pending_confirmation_count。
- [ ] AA009 StandardMetric create 可用。
- [ ] AA010 StandardMetric patch 可用。
- [ ] AA011 MetricAlias list 可用。
- [ ] AA012 MetricAlias create 可用。
- [ ] AA013 MetricAlias patch 可用。
- [ ] AA014 OCR metric issue query 可用。
- [ ] AA015 OCR task query 可用。
- [ ] AA016 不存在正式 LabResult edit Admin API。
- [ ] AA017 不存在 OCR result edit Admin API。

---

# 23. Admin Web

- [ ] AW001 登录页可用。
- [ ] AW002 登录成功进入后台。
- [ ] AW003 未登录访问管理页会被正确处理。
- [ ] AW004 有清晰的基础导航。
- [ ] AW005 StandardMetric 列表可用。
- [ ] AW006 可新增 StandardMetric。
- [ ] AW007 可编辑 name/category。
- [ ] AW008 UI 中 code 在创建后只读。
- [ ] AW009 可停用 / 恢复 StandardMetric。
- [ ] AW010 pending Confirmation 阻断停用时 UI 显示明确错误。
- [ ] AW011 StandardMetric 详情 / Alias 列表可用。
- [ ] AW012 可新增 Alias。
- [ ] AW013 可编辑 Alias 文本/type。
- [ ] AW014 Alias target 创建后不能直接改成其它 metric。
- [ ] AW015 可停用 / 恢复 Alias。
- [ ] AW016 Alias 冲突错误可理解。
- [ ] AW017 OCR 未匹配名称列表可用。
- [ ] AW018 可从未匹配项打开创建 Alias 流程。
- [ ] AW019 产品主数据缺失 code 列表可用。
- [ ] AW020 可从缺失 code 打开创建 StandardMetric 流程。
- [ ] AW021 OCR Task 只读列表可用。
- [ ] AW022 loading 状态可用。
- [ ] AW023 empty 状态可用。
- [ ] AW024 API error 状态可用。
- [ ] AW025 Stage 07 不要求进行全站视觉重构。

---

# 24. Migration

- [ ] MG001 新 migration 基于当前 0006 HEAD。
- [ ] MG002 migration revision 为新的 0007。
- [ ] MG003 0007 新增 StandardMetric.category。
- [ ] MG004 0007 创建 metric_aliases。
- [ ] MG005 0007 创建必要索引。
- [ ] MG006 0007 创建可靠 Alias 唯一约束。
- [ ] MG007 upgrade 成功。
- [ ] MG008 downgrade 至 0006 成功。
- [ ] MG009 再 upgrade 至 0007 成功。
- [ ] MG010 全新数据库 0001 → 0007 成功。
- [ ] MG011 不修改 0001～0006 文件。
- [ ] MG012 migration 不批量写入 PoC 74 项。
- [ ] MG013 migration 不 backfill LabResult。
- [ ] MG014 migration 不 backfill ConfirmationItem。
- [ ] MG015 migration 不改 OcrResultItem。
- [ ] MG016 autogenerate 产生的 Stage 03 无关索引 drift 被明确排除。
- [ ] MG017 0007 不顺手修复 Stage 03 已知 ORM/migration 漂移。

---

# 25. PostgreSQL 17 专项

- [ ] PG001 PostgreSQL 17 空库 migration 通过。
- [ ] PG002 PostgreSQL 17 0006 → 0007 migration 通过。
- [ ] PG003 PostgreSQL 17 downgrade / re-upgrade 通过。
- [ ] PG004 StandardMetric code 唯一约束真实有效。
- [ ] PG005 MetricAlias ACTIVE normalized uniqueness 真实有效。
- [ ] PG006 两个并发相同 Alias 创建只能成功一个。
- [ ] PG007 namespace 冲突在 PostgreSQL 真实环境验证。
- [ ] PG008 pending Confirmation 停用保护在 PostgreSQL 真实环境验证。
- [ ] PG009 测试创建的临时数据库最终删除，无残留。

---

# 26. OCR Frozen Boundary

- [ ] OF001 `backend/ocr_runtime/src/metric_matcher.py` 未修改。
- [ ] OF002 `backend/ocr_runtime/src/paper_metric_matcher.py` 未修改。
- [ ] OF003 `backend/ocr_runtime/data/metric_library.json` 未修改。
- [ ] OF004 AUTO_THRESHOLD 未修改。
- [ ] OF005 REVIEW_THRESHOLD 未修改。
- [ ] OF006 MIN_MARGIN 未修改。
- [ ] OF007 fuzzy scoring 未修改。
- [ ] OF008 unit scoring 未修改。
- [ ] OF009 OCR retry 规则未修改。
- [ ] OF010 FINAL_AUTO / FINAL_REVIEW 判定逻辑未修改。
- [ ] OF011 Worker 不动态加载数据库 MetricAlias 改写 OCR matcher。
- [ ] OF012 Pipeline version 未因 Stage 07 修改。

---

# 27. Stage 04 回归

- [ ] R401 微信端已有报告可正常进入确认工作区。
- [ ] R402 REVIEW_PENDING 阻断继续有效。
- [ ] R403 REVIEW 人工确认继续有效。
- [ ] R404 AUTO 主动修改继续有效。
- [ ] R405 StandardMetric 手工选择继续有效。
- [ ] R406 KEEP_ORIGINAL_NAME 继续有效。
- [ ] R407 手工补项继续有效。
- [ ] R408 纯手工报告继续有效。
- [ ] R409 Confirmation workspace 退出重进继续恢复。
- [ ] R410 commit 幂等继续有效。
- [ ] R411 OcrResultItem 不可变自动测试继续通过。
- [ ] R412 已初始化旧 workspace 不因 Alias 变化。

---

# 28. Stage 05 回归

- [ ] R501 正式报告列表正常。
- [ ] R502 正式报告详情正常。
- [ ] R503 原图查看正常。
- [ ] R504 正式报告主项目名称仍使用 LabResult.metric_name。
- [ ] R505 报告迁移正常。
- [ ] R506 报告删除正常。
- [ ] R507 HealthProfile 隔离正常。
- [ ] R508 Stage 07 Admin 不直接编辑正式报告。

---

# 29. Stage 06 回归

- [ ] R601 我的指标列表正常。
- [ ] R602 latest 正常。
- [ ] R603 history 正常。
- [ ] R604 trend 正常。
- [ ] R605 同日多次保留正常。
- [ ] R606 comparator / 非数值安全行为正常。
- [ ] R607 多单位趋势分组正常。
- [ ] R608 Favorite 正常。
- [ ] R609 StandardMetric rename 后聚合 identity 不分裂。
- [ ] R610 StandardMetric inactive 后既有历史仍可见。
- [ ] R611 standard_metric_id=NULL 的正式结果仍不自动进入 Stage 06 聚合。
- [ ] R612 新 Alias 不改变 Stage 06 既有数据。

---

# 30. 自动测试命令验收

最终必须运行并记录真实结果：

- [ ] AT001 Backend 全量 pytest 通过。
- [ ] AT002 Backend Ruff 通过。
- [ ] AT003 Miniapp tests 通过。
- [ ] AT004 Miniapp typecheck 通过。
- [ ] AT005 Miniapp 微信构建通过。
- [ ] AT006 Admin typecheck 通过。
- [ ] AT007 Admin build 通过。
- [ ] AT008 PostgreSQL 17 Stage 07 专项通过。
- [ ] AT009 既有 PostgreSQL 集成测试继续通过。
- [ ] AT010 `git diff --check` 通过。

如仓库实际命令与旧阶段不同：

```text
以最新 package / pyproject / README / AGENTS 为准
```

不得伪造未运行的测试结果。

---

# 31. 人工验收场景

以下人工验收由项目负责人在真实 Admin Web / 微信环境完成。

## T01｜Admin 登录与权限隔离

前置：

```text
Stage 07 后端 / Admin Web 已启动
配置有效管理员凭据
```

步骤：

1. 未登录直接访问管理页；
2. 使用错误管理员密码登录；
3. 使用正确管理员密码登录；
4. 正常进入管理后台；
5. 验证普通用户 Token 不能调用 Admin API；
6. 验证 Admin Token 不能作为微信普通用户身份访问用户业务数据。

期望：

```text
PASS：
未登录有正确处理；
错误密码失败；
正确密码成功；
Admin / User 权限边界成立。
```

结果：

```text
负责人真实人工验收：PENDING
```

---

## T02｜StandardMetric 新增 / 编辑 / code 不可变

步骤：

1. Admin 新建一个测试 StandardMetric；
2. 填写 code / name / category；
3. 保存；
4. 修改 name；
5. 修改 category；
6. 尝试修改 code。

期望：

```text
PASS：
创建成功；
name/category 可修改；
code 不可修改；
错误反馈明确。
```

结果：

```text
负责人真实人工验收：PENDING
```

---

## T03｜StandardMetric 停用 / 恢复与 pending 保护

步骤：

1. 选择一个没有 PENDING Confirmation 引用的测试指标；
2. 停用；
3. 恢复；
4. 创建 / 准备一个 PENDING_CONFIRMATION 工作区并让 ConfirmationItem 引用某 ACTIVE 指标；
5. Admin 尝试停用该指标。

期望：

```text
PASS：
普通停用/恢复正常；
存在 pending 引用时停用被阻止；
已有工作区不会被管理员操作直接卡死。
```

结果：

```text
负责人真实人工验收：PENDING
```

---

## T04｜MetricAlias 管理与冲突

步骤：

1. 为测试指标新增 Alias；
2. 新增不同类型 Alias；
3. 编辑 Alias；
4. 停用 / 恢复 Alias；
5. 尝试新增 normalized 后相同 Alias；
6. 尝试让 Alias 与其它 StandardMetric code/name 冲突。

期望：

```text
PASS：
正常维护成功；
重复 / namespace 冲突被拒绝；
恢复时仍做冲突检查。
```

结果：

```text
负责人真实人工验收：PENDING
```

---

## T05｜小程序 Alias 搜索

步骤：

1. 创建一个用户不容易通过 canonical name 找到、但 Alias 清晰的测试 Alias；
2. 进入 Stage 04 标准指标选择；
3. 输入 Alias 搜索。

期望：

```text
PASS：
搜索命中 canonical StandardMetric；
最终保存的是 StandardMetric，不是 Alias。
```

结果：

```text
负责人真实微信人工验收：PENDING
```

---

## T06｜Alias 对 REVIEW 的安全预关联

前置：

准备一个满足：

```text
FINAL_REVIEW
+
raw_metric 可被新增 Alias exact 命中
+
Confirmation workspace 尚未初始化
```

的 OCR 任务。

步骤：

1. Admin 创建 Alias；
2. 用户第一次打开该报告确认页；
3. 查看对应项目。

期望：

```text
PASS：
standard_metric_id 可以被预关联；
项目仍然是待确认；
不能因为 Alias 自动通过 REVIEW；
用户仍需人工确认。
```

结果：

```text
负责人真实微信人工验收：PENDING
```

---

## T07｜已初始化 Confirmation 不重算

步骤：

1. 打开一个尚未命中标准指标的待确认报告，形成 ConfirmationItem；
2. 退出；
3. Admin 新建能够命中该 raw_metric 的 Alias；
4. 再次打开同一确认工作区。

期望：

```text
PASS：
原 ConfirmationItem 不自动变化；
仍保持首次初始化后的状态；
用户可以手工选择新的 StandardMetric。
```

结果：

```text
负责人真实微信人工验收：PENDING
```

---

## T08｜历史正式报告不回填

步骤：

1. 找一个已 commit 且 `standard_metric_id=NULL` 的正式项目；
2. Admin 新建能 exact 命中其名称的 Alias；
3. 查看该正式报告；
4. 查看 Stage 06 我的指标。

期望：

```text
PASS：
历史 LabResult 不被重关联；
正式报告保持原事实；
该项目不因新 Alias 自动进入 Stage 06 聚合。
```

结果：

```text
负责人真实微信人工验收：PENDING
```

---

## T09｜StandardMetric rename 的展示边界

步骤：

1. 选择一个已有正式 LabResult 的 StandardMetric；
2. 记录旧正式报告中的项目名称；
3. Admin 修改 StandardMetric.name；
4. 查看 Stage 06；
5. 查看旧正式报告详情。

期望：

```text
PASS：
Stage 06 使用新 canonical name；
聚合历史不分裂；
旧正式报告主名称仍保持 LabResult.metric_name；
标准指标辅助信息可显示新 canonical name。
```

结果：

```text
负责人真实微信人工验收：PENDING
```

---

## T10｜StandardMetric inactive 后历史继续可见

步骤：

1. 选择一个已有 Stage 06 历史 / trend 的 StandardMetric；
2. Admin 停用；
3. 进入我的指标；
4. 打开历史；
5. 打开趋势；
6. 如已收藏，检查 Favorite。

期望：

```text
PASS：
历史 / latest / trend / favorite 均继续存在；
停用只影响未来选择与预关联。
```

结果：

```text
负责人真实微信人工验收：PENDING
```

---

## T11｜OCR 未匹配名称 → 创建 Alias

步骤：

1. Admin 打开 OCR 指标问题；
2. 查看未匹配名称；
3. 选择一条真实可确认的问题；
4. 创建 Alias；
5. 返回问题列表。

期望：

```text
PASS：
可看到聚合次数/最近时间等轻量信息；
创建 Alias 成功；
问题按当前主数据规则不再作为 pending unmatched；
历史 OcrResultItem 未被修改。
```

结果：

```text
负责人真实人工验收：PENDING
```

---

## T12｜OCR 缺失产品 StandardMetric → 创建主数据

步骤：

1. 找到 OCR 已识别 code、但产品 StandardMetric 缺失的问题；
2. 打开创建 StandardMetric；
3. 检查 code/name 预填；
4. 管理员确认创建；
5. 返回问题列表。

期望：

```text
PASS：
主数据可补充；
不会自动导入 PoC 全量 74 项；
历史 OCR 快照和旧 Confirmation 不重算。
```

结果：

```text
负责人真实人工验收：PENDING
```

---

## T13｜OCR Task 只读排查

步骤：

1. 打开 OCR Task 页面；
2. 按 status 筛选；
3. 按 pipeline version 筛选；
4. 查看任务摘要。

期望：

```text
PASS：
能查看任务状态与轻量工程信息；
没有重跑、改状态、强制成功、改结果等危险操作。
```

结果：

```text
负责人真实人工验收：PENDING
```

---

# 32. 安全回归阻断项

最终人工验收前必须再次确认：

- [ ] SAFE001 OcrResultItem 不可变。
- [ ] SAFE002 Alias 不提升 REVIEW 信任等级。
- [ ] SAFE003 历史正式 LabResult 不批量重关联。
- [ ] SAFE004 StandardMetric 停用不隐藏既有医疗历史。
- [ ] SAFE005 Admin 不直接编辑正式医疗结果。
- [ ] SAFE006 OCR matcher 未改。
- [ ] SAFE007 Pipeline version 未改。
- [ ] SAFE008 PoC 74 项未被自动全量导入产品主数据。
- [ ] SAFE009 Stage 03 既有 migration drift 未被顺手修复。
- [ ] SAFE010 Admin 日志不泄露密码 / token / 完整医疗数据。

---

# 33. 文档验收

Stage 07 实施过程中至少维护：

- [ ] DOC001 `docs/stages/07-admin/PLAN.md` 保持冻结设计基线。
- [ ] DOC002 `docs/stages/07-admin/ACCEPTANCE.md` 保持冻结验收基线。
- [ ] DOC003 实施完成后新增 / 更新 `docs/stages/07-admin/RESULT.md`。
- [ ] DOC004 RESULT 记录真实修改内容。
- [ ] DOC005 RESULT 记录 migration。
- [ ] DOC006 RESULT 记录真实自动测试结果。
- [ ] DOC007 RESULT 记录 PostgreSQL 17 专项结果。
- [ ] DOC008 RESULT 记录所有人工 T01～T13。
- [ ] DOC009 RESULT 记录偏差。
- [ ] DOC010 RESULT 记录已知非阻塞问题。
- [ ] DOC011 若长期模型说明发生变化，必要 architecture 文档同步。
- [ ] DOC012 不把 Stage 07 大量实现细节复制进 AGENTS.md。

---

# 34. 最终 PASS 条件

只有同时满足：

```text
全部 P0 / SAFE = PASS
+
全部自动测试 = PASS
+
PostgreSQL 17 专项 = PASS
+
Admin build/typecheck = PASS
+
Miniapp 既有回归 = PASS
+
负责人真实人工验收 T01～T13 = PASS
+
OCR runtime 未修改
+
0001～0006 未修改
+
Stage 03 migration drift 未顺手修复
+
RESULT.md 完成
```

才能：

```text
Stage 07 = PASS
```

在负责人尚未完成人工验收前：

```text
不得把 RESULT.md 写成最终 PASS
```

最多标记：

```text
AUTOMATED PASS / WAITING MANUAL ACCEPTANCE
```

---

# 35. 验收结论模板

最终 RESULT 可使用：

```text
Stage 07：PASS / FAIL

自动验证：
- Backend:
- Ruff:
- PostgreSQL 17:
- Miniapp tests:
- Miniapp typecheck:
- Miniapp 微信构建:
- Admin typecheck:
- Admin build:
- git diff --check:

人工验收：
- T01:
- T02:
- T03:
- T04:
- T05:
- T06:
- T07:
- T08:
- T09:
- T10:
- T11:
- T12:
- T13:

安全边界：
- OcrResultItem immutable:
- Alias does not promote REVIEW:
- Historical LabResult not relinked:
- OCR runtime unchanged:
- Pipeline version unchanged:
- Stage 03 migration drift untouched:

偏差：
- ...

已知非阻塞问题：
- ...

最终结论：
- ...
```
