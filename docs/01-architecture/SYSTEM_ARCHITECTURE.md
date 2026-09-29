# SYSTEM_ARCHITECTURE｜系统架构

## 1. 组件

### 客户端
- 微信小程序：主要用户入口；
- Web Admin：标准指标、别名、分类与 OCR 问题排查。

### 服务端
- Nginx：生产 HTTPS 和反向代理；
- FastAPI：所有业务 API；
- PostgreSQL：业务数据 + OCR 持久化任务队列；
- OCR Worker：独立进程执行 OCR Pipeline；
- 腾讯云 COS：原始报告和 OCR 长期产物。

## 2. 关键调用链

### 上传
`Miniapp → FastAPI 鉴权/签发上传信息 → COS → FastAPI 登记 Asset`

### OCR
`Miniapp → FastAPI 创建 Task → PostgreSQL QUEUED → Worker 领取 → Pipeline → OCR 快照 → Confirmation`

### 正式保存
`Miniapp → FastAPI commit → 校验 REVIEW/重复 → DB transaction → LabReport + LabResult`

### 趋势
`Miniapp → FastAPI → LabResult(正式数据) → StandardMetric + unit series → trend/history`

## 3. 进程边界

FastAPI 不同步执行长 OCR。
OCR Worker 不创建正式报告。
Admin 不直接编辑正式用户 LabResult。

## 4. 演进原则

只有在明确出现任务吞吐/并发瓶颈后才评估 Redis/Celery 等；只有单体维护困难且有清晰服务边界时才评估微服务。
