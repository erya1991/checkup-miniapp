# D-0002｜V1.0 OCR 任务使用 PostgreSQL 持久化队列

日期：2026-09-29  
状态：Accepted

## 决定

OCR 使用独立 Worker，但 V1.0 使用 PostgreSQL 保存 QUEUED/PROCESSING/SUCCEEDED/FAILED 任务，不引入 Redis/Celery/RabbitMQ。

## 原因

- OCR 必须脱离 HTTP 请求执行；
- 任务需要重启不丢；
- 当前负载很低；
- 减少 4C4G 服务器上的组件和运维成本。

## 影响

Worker 领取必须实现数据库原子竞争控制；初期并发固定为 1。

## 重新评估条件

OCR 排队明显、需要多机 Worker 或任务吞吐成为瓶颈。
