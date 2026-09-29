# TECH_BASELINE｜检查单小程序 MVP V1.0 技术基线

## 1. 总体架构

```text
微信小程序（uni-app）
        │ HTTPS
        ▼
      Nginx
        │
        ▼
   FastAPI 单体业务服务
     │       │        │
     │       │        └─ 腾讯云 COS（私有）
     │       │
     │       └─ PostgreSQL 17
     │
     └─ OCR Task（数据库持久化队列）
               │
               ▼
         独立 OCR Worker
               │
               ▼
       已验证 Python OCR Pipeline

Web Admin（Vue3/Vite/Element Plus）→ 同一 FastAPI
```

## 2. 技术栈

| 层级 | V1.0 技术 |
|---|---|
| Miniapp | uni-app + Vue3 + TypeScript |
| Admin Web | Vue3 + Vite + Element Plus + TypeScript |
| Backend | Python 3.12.10 + FastAPI |
| ORM | SQLAlchemy 2.x |
| Migration | Alembic |
| Database | PostgreSQL 17 |
| File | Tencent COS private bucket |
| OCR | Existing Python OCR Pipeline |
| OCR execution | Independent Python Worker |
| Queue | PostgreSQL persistent task queue |
| Deployment | Docker Compose + Nginx |

## 3. 为什么采用单体后端

V1.0 用户规模小、功能边界明确，主要复杂度在 OCR 数据安全闭环，不在高并发。

目标是：
- 一个业务服务；
- 一个数据库；
- 一个独立 OCR Worker；
- 文件放 COS；
- 避免引入不必要的中间件和运维复杂度。

## 4. OCR 执行边界

OCR 不能在普通 HTTP 请求中同步长时间执行，也不把正式重任务寄托于轻量后台回调。

流程：

```text
POST recognize
→ 创建 OcrTask(QUEUED)
→ API 立即返回
→ OCR Worker 原子领取任务
→ PROCESSING
→ 执行 Pipeline
→ 保存 OCR 快照/产物
→ 初始化 ConfirmationItem
→ SUCCEEDED / FAILED
```

V1.0 Worker 并发默认 1。

## 5. 数据域隔离

严格区分：

### 导入/确认域
- ReportIngestion；
- ReportAsset；
- OcrTask；
- OcrResultItem；
- ConfirmationItem。

### 正式报告域
- LabReport；
- LabResult。

正式历史查询只读正式报告域。

## 6. 核心数据链

```text
User
→ HealthProfile
→ ReportIngestion
→ ReportAsset
→ OcrTask
→ OcrResultItem（不可覆盖）
→ ConfirmationItem（用户确认工作区）
→ commit
→ LabReport
→ LabResult
→ StandardMetric
→ History / Trend
```

含义：
- ReportAsset = 原始报告事实；
- OcrResultItem = 机器当时识别事实；
- ConfirmationItem = 用户确认过程；
- LabResult = 正式健康数据。

## 7. 文件存储

生产原始报告和长期 OCR 审计产物使用腾讯云 COS 私有桶。

小程序上传推荐：
- 后端鉴权；
- 后端签发受限临时上传权限/上传信息；
- 客户端直传 COS；
- 后端登记 object key。

原始文件路径不得使用姓名、关系、医院名称等个人信息作为目录。

## 8. 趋势数据

V1.0 不建立独立 Trend 表。

趋势实时/按需基于 LabResult 查询：
- `health_profile_id`；
- `standard_metric_id`；
- `unit_normalized`；
- `examination_date/time`。

只有可绘制数值进入普通 trend points；所有结果进入 history。

## 9. 安全边界

- 全站 HTTPS；
- 微信身份换取系统自己的登录 Token；
- 每个业务资源校验当前用户所有权；
- COS 私有访问；
- Secret 只存在服务端安全环境；
- 不记录敏感医疗全文到普通日志；
- 测试数据脱敏。

## 10. 删除边界

删除正式报告后：
- 立即退出报告/指标/趋势查询；
- 清理对应正式结果；
- 触发/执行原始文件与 OCR 产物清理。

删除健康档案需受控清理其报告、结果、关注、导入、OCR 与文件，不能只依赖数据库级联。

## 11. 当前部署资源约束

目标服务器：
- 4 CPU；
- 4 GB RAM；
- 40 GB SSD；
- 3 Mbps。

建议初期：
- FastAPI：1～2 worker；
- OCR Worker：1；
- OCR 并发：1；
- PostgreSQL：1；
- Nginx：1。

服务器本地磁盘仅作为数据库、日志、Docker 和 OCR 临时目录；原图长期放 COS。

## 12. V1.0 非技术范围

默认不使用：Redis、Celery、RabbitMQ、Kafka、MongoDB、Elasticsearch、微服务、Kubernetes、分布式事务、复杂网关/配置中心。

只有出现明确瓶颈并经过决策记录后才允许演进。
