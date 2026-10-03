# Stage 09｜整体产品化 + 统一 UI / UX：实施结果

实施日期：2026-10-03～2026-10-04。

**当前状态：AUTOMATED PASS / WAITING MANUAL ACCEPTANCE。Stage 09 尚未最终 PASS。** Backend、PostgreSQL 17、Miniapp 和 Admin 自动验证通过；项目负责人真实微信 T01～T11、Admin T12 均为 PENDING，不以源码、页面脚本测试或构建替代。

## 1. 基线与实施范围

- 开始时分支 main，HEAD / fetch 后 origin/main 均为 `524351d35121ac3519fb9c1e665663a59205f1a6`。只有本目录 PLAN / ACCEPTANCE 两个未跟踪文件；视为用户提供的冻结实施基线，未发现其它未知修改。
- 从该基线创建 `stage/09-productization-ui-ux`，按 AGENTS 顺序读取长期基线、Stage09 PLAN / ACCEPTANCE、Stage08 RESULT，并核对 Stage03～07 RESULT、architecture 与当前前端真实代码。Stage00～08 原验收事实保持。
- 按 A～G 分批实施。Batch A 先通过 47 项 tests、typecheck、微信 build，再放行其余前端批次；后续分批验证及独立代码复核，最终重新执行 Miniapp 全量验证。
- 本轮使用 `wechat-miniapp-design` 及官方指南摘要；未依赖 Stitch 或其它外部视觉稿。仅前端展示、交互、相关测试与交付文档，未新增后端 API。

## 2. 信息架构、页面与实际完成项

| 批次 | 实际实现 |
| --- | --- |
| A 基础 / 一级模块 | 原生首页 / 报告 / 我的三 Tab；报告内检验报告 / 我的指标两视角；一级导航使用 switchTab；首页主动作固定新上传，展示多待处理总数与最高优先级报告、最近两份正式报告、最多三个关注指标；“我的”提供档案管理、隐私与产品边界说明 |
| B 报告产生 | 待处理列表仅未完成 ingestion；指定身份继续处理，无身份上传不查找或复用旧报告；上传页原图、页序、追加/移除/排序、进度、单图重试；识别页说明后台继续、识别完成仍待核对、失败重识别/保留原图手工录入 |
| C 人工核对 | 首屏流程与实时需要核对数、原图、报告基本信息、优先核对、折叠已采用/已移除、手工补项、关联指标搜索、按报告原名称保存及趋势排除说明、字段原位错误、底部确认并保存；仍可修改自动采用项和恢复移除项 |
| D 正式报告 | 卡片优先日期/医院/分类/项目数/持久异常数；详情继续正式 metric_name / result_text / 单次参考范围；未关联指标说明；原图主入口；迁移/永久删除进入更多操作，保留重复确认和危险确认；删除回稳定报告 Tab |
| E 指标 / 趋势 | MetricList 嵌入报告 Tab，旧指标路由兼容导向该视角；canonical 名称、latest、关注状态、完整历史；多单位切换、同日多次与文本结果保持；趋势横向滚动、逐点身份/真实结果/参考/异常/来源报告；日期拆分、rpx 字号与点击区域 |
| F 健康档案 | 当前档案 Tag、中文关系、切换/编辑/更多层级；永久删除仍调用既有影响预览及删除 helper；新建编辑保留原字段、picker、loading、防双击和字段错误；最后档案删除后可重新创建 |
| G Admin | 7 个 views 与 shell、工具栏、表格 Tag、Dialog、loading/empty/error/retry 统一；指标详情保持标准指标菜单选中；停用危险视觉；复用 Element Plus，不新增管理业务 |

首页、报告、指标与档案请求使用页面级 guard，切档案/页面隐藏时清除旧上下文并拒绝晚返回写入；不建立全局业务列表 Store。报告列表与首页最近报告保持服务端顺序，异常只读已持久化标记。

## 3. 公共组件与 Skill 落地点

- `miniapp/src/styles/tokens.css`：背景、文字、状态色、字体层级、间距、圆角、按钮、字段、卡片与安全区的统一来源。375px / 750rpx 布局基准，不使用装饰渐变/大型 UI 库。
- `PageContainer / UiState / StatusTag / ProfileContext`：页面容器、loading/empty/error/retry、状态语义与统一档案上下文；`MetricList` 为报告模块第二视角。趋势图继续使用原有轻量组件。
- 原生 TabBar / 导航栏承担一级导航、返回和官方菜单区域；原生 picker、拍照/相册、图片预览、Modal、ActionSheet 处理选择和确认。普通错误保留原位说明及恢复路径，成功可用轻量 Toast。
- getAppBaseInfo 的字体倍率/字号设置统一转为 1～2 倍文本与控件尺寸；内容换行、按钮高度随字体变化，底部保留 safe-area。字体档位、真实热区、原生页栈仍待微信 T01/T11 等人工验证。
- Admin 新增 `PageHeader / QueryError / StatusTag` 与公共 CSS / presentation helper，保持原有业务、时间 formatter 和权限。

## 4. 历史体验债务与复核修正

- “识别任务记录”改为“待处理报告”；多份未完成报告均保留，不再依赖单一 draft/find。
- 待处理及 OCR 页仅可显示机器初次 total_count，不展示旧 auto_count/review_count 为当前进度；核对页从真实 items 分组计算需要核对数量。
- 新上传与指定继续明确分离；识别完成与正式保存分别表达；工程枚举转为普通用户文案。code 在核对搜索结果中保留为次级辅助。
- 按报告原名称保存说明不关联标准指标、不参与我的指标趋势，不修改实际身份。
- 独立复核修复：上传期间禁止重载；登记成功后列表刷新失败不再进入重复上传队列；清空旧档案标题；离开上传/OCR页后迟到操作不突然导航；仅当前档案切换按钮显示 loading。
- 新增真实 Confirmation 页面脚本测试时发现 Vue 异步字段 watcher 会清空刚设置的日期错误，改为同步清除旧错误后校验；不改变保存校验或 payload。

## 5. 自动验证真实结果

| cwd | 命令 | 真实结果 |
| --- | --- | --- |
| backend | `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp runtime/stage09` | PASS，124 passed，0 failed / skipped，63.32 秒；1 条既有 TestClient 弃用提示 |
| backend | `.venv/Scripts/ruff.exe check . --no-cache` | PASS |
| backend | `.venv/Scripts/alembic.exe heads` | 唯一 `0008_profile_data_deletion (head)` |
| miniapp | `pnpm test` | PASS，67 tests，0 failed / skipped；原 42 项保留，新增 25 项 |
| miniapp | `pnpm typecheck` | PASS |
| miniapp | `pnpm build:mp-weixin` | PASS，Build complete，`dist/build/mp-weixin` |
| admin-web | `pnpm test` | PASS，10 tests，0 failed / skipped；原 7 项保留，新增 3 项 |
| admin-web | `pnpm typecheck` | PASS |
| admin-web | `pnpm build` | PASS，Vite 构建完成 |
| root | `git diff --check` | PASS |

Miniapp 新增测试覆盖三 Tab/路由、新上传与指定任务、待处理优先级/数量、正式摘要、字体/安全错误、NULL身份说明、日期表达、登记成功后刷新失败、真实核对页面的 REVIEW/日期阻断、重复确认/ack、失响应恢复、防重复保存等。既有 payload、guard、单位、趋势、权限、删除恢复断言保留；仅 canonical 主文案断言由 name(code) 改为 name，同时单独保留 code 事实断言。不删除、skip或弱化业务安全断言。

## 6. PostgreSQL 17 既有专项

环境 PostgreSQL 17.11。以下六组本轮实际执行均 exit 0 / PASS，不沿用旧 RESULT 的通过结论：

| 脚本（backend 下 `.venv/Scripts/python.exe tests/…`） | 本轮验证 |
| --- | --- |
| `verify_postgres_queue.py` | Stage03 SKIP LOCKED、Worker/advisory lock、lease/恢复、来源唯一约束 |
| `verify_postgres_confirmation.py` | Stage04 历史/空库迁移、真实并发初始化/commit、事务回滚、唯一约束、OCR不可变；两库清理 |
| `verify_postgres_reports.py` | Stage05迁移/删除/归属/并发/回滚、PREFIX/OBJECT清理与失败重试；两库清理 |
| `verify_postgres_metrics.py` | Stage06正式历史、排序/同日多次/多单位/数值准入/Favorite权限并发、迁移删除；两库清理 |
| `verify_postgres_stage07.py` | Stage07主数据/namespace/Alias并发、pending/commit/init保护、UNMATCHED身份和快照、历史兼容；两库清理 |
| `verify_postgres_profile_deletion.py` | Stage08增量/空库、全链删除/回滚/真实竞态/PROCESSING阻断、授权窗口/late object/retry；两库清理 |

专项结束后另行独立查询 `pg_database`，`checkup_stage0%` 临时库残留为 0。只使用脚本创建的 UUID 隔离库和合成 COS 替身，不迁移业务库，不操作真实 COS，不启动/重启验收 API 或 Worker。日志在忽略目录 `backend/runtime/stage09-*.log`。

## 7. 冻结边界、差异与限制

- 相对实施基线，整个 `backend/` tracked diff = 0，冻结目录无新增 untracked；0 migration，0001～0008、模型、OCR runtime/Worker/queue/Pipeline、matcher/threshold/unit scoring/retry/evidence均未修改。
- Pipeline Version 保持 `poc-sha256:9f0c4c4c61351c84894a37cc4f44d3f8dd77003b40bcbd67a1bf34bc825ab6e6`；机器快照不可变、REVIEW解决准入、MetricAlias首次初始化边界、历史正式事实、持久 abnormal、标准身份、Stage08删除链与Stage06单位/时间规则保持。
- Stage03 两项历史 index drift 保持；不宣称全库 alembic check 无差异。不新增医疗判断、换算、回填或 Stage10 能力。
- PLAN / ACCEPTANCE 保持原文，本轮不写入它们；交付 SHA256 分别为 `99e7e1eda1480934b49030563c6347485fb4397bd00f455d67efdf7674bced7b`、`3d2aa26195d1468045701cf4b841c290af9b44f638721ffbf50879b2d1829d3a`。
- 允许的实现组织差异：指标视角抽为 MetricList；旧路由保留兼容跳转；原生 Tab 使用文字与颜色区分，未增加装饰图标（C009/R015为P1）。无schema或产品规则偏差。
- 既有 Node module type提示、uni-app更新通知、Admin大包提示、TestClient弃用提示保持，不为本阶段升级依赖或拆包。
- 本地Admin 5199端口被Windows EACCES拒绝，17839启动成功；浏览器工具连接超时，未得到浏览器点击验收。临时预览服务已停止。该检查失败不写作负责人T12结果。
- 微信构建已生成可导入目录，未代操作微信开发者工具；真机字体、热区、长报告、返回栈、真实上传/OCR和Admin主流程体验待负责人验收。

## 8. 负责人待人工验收

请将 `miniapp/dist/build/mp-weixin` 导入微信开发者工具，按冻结 ACCEPTANCE 在真实微信环境执行；使用合成或脱敏样本，保留原图核对。现有Backend功能不变，本轮没有替负责人启动验收服务。

| 编号 | 场景 | 状态 / 归属 |
| --- | --- | --- |
| T01 | 三 Tab、报告/指标/原图返回路径 | PENDING，负责人真实微信 |
| T02 | 至少两个档案全局切换与旧请求保护 | PENDING，负责人真实微信 |
| T03 | 新上传与至少两份未完成报告 | PENDING，负责人真实微信 |
| T04 | 多页上传、识别期间离开重进、阶段感 | PENDING，负责人真实微信 |
| T05 | 核对/自动项编辑/指标选择/原名保存/补项/重进/最终保存 | PENDING，负责人真实微信 |
| T06 | 已处理REVIEW后待处理入口不再显示旧进度 | PENDING，负责人真实微信 |
| T07 | 正式报告事实、原图、迁移与删除 | PENDING，负责人真实微信 |
| T08 | Favorite、latest/history/trend、多单位/非数值、逐点追溯 | PENDING，负责人真实微信 |
| T09 | 首页正式摘要、异常/关注/待处理边界 | PENDING，负责人真实微信 |
| T10 | 档案新增/编辑/切换/默认及最后档案永久删除/重建 | PENDING，负责人真实微信 |
| T11 | 无档案/报告/指标/趋势/待处理、网络重试、OCR失败；并核对大字体核心流程 | PENDING，负责人真实微信 |
| T12 | Admin登录/导航/指标/别名/Issue/Task/空页/错误重试 | PENDING，负责人Admin |

AC004 构建产物导入工具和 R014 字体放大实机表现也需负责人给出真实确认。所有适用 P0 与负责人人工结果齐备前不标最终 PASS。

## 9. Git 与停止点

- 实施基线与 main / origin/main：`524351d35121ac3519fb9c1e665663a59205f1a6`。
- 交付分支：`stage/09-productization-ui-ux`；提交标题 `feat: productize stage 09 interfaces`。该提交包含本轮前端、测试、说明及本RESULT；实际SHA以本轮最终汇报或 `git log -1 --format=%H -- docs/stages/09-productization-ui-ux/RESULT.md` 定位。
- 用户已允许阶段分支正常提交；本轮不推送、不合并main、不重写历史。main / origin/main保留上述基线。
- 停止于工程实施完成、等待负责人真实验收；未进行Stage09最终PASS收尾、Stage10、部署或发布。
