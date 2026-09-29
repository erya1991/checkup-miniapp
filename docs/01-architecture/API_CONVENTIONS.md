# API_CONVENTIONS｜API 约定

## 1. 基础

- 前缀：`/api/v1`；
- JSON 为默认业务格式；
- 资源访问必须校验当前用户所有权；
- 分页、排序、过滤参数在各阶段再具体冻结。

## 2. 主要资源路径

```text
/auth
/me
/health-profiles
/ingestions
/reports
/profile-metrics
/favorites
/admin
```

## 3. 统一业务错误

建议：

```json
{
  "code": "REVIEW_PENDING",
  "message": "存在待确认项目",
  "request_id": "req_xxx",
  "details": {
    "pending_count": 2
  }
}
```

前端基于 `code` 分支。

重点错误码：
- `AUTH_REQUIRED`；
- `PROFILE_NOT_FOUND`；
- `REPORT_NOT_FOUND`；
- `UPLOAD_FAILED`；
- `OCR_TASK_FAILED`；
- `OCR_RESULT_NOT_READY`；
- `REVIEW_PENDING`；
- `INVALID_REPORT_DATE`；
- `DUPLICATE_CONFIRM_REQUIRED`；
- `FILE_ACCESS_DENIED`。

## 4. 幂等

必须重点保护：
- 开始 OCR；
- commit；
- 删除类接口。

特别是同一 ingestion 重复 commit 只能对应一份 LabReport。

## 5. 关键 API 方向

### Auth
- `POST /auth/wechat`
- `POST /auth/refresh`
- `GET /me`

### Health Profile
- CRUD `/health-profiles`
- `PUT /me/default-health-profile`

### Ingestion
- `POST /ingestions`
- upload authorization / asset register / reorder / delete
- recognize / retry
- confirmation read/update
- items add/update/remove
- `POST /ingestions/{id}/commit`

### Report
- list/detail/assets
- migrate health profile
- delete

### Metrics
- profile metrics list
- metric history
- metric trend
- favorite/unfavorite

## 6. Admin

Admin API 与用户业务 API 共享 FastAPI，但使用独立 `/admin` 路由和管理员权限。OCR 问题页默认只读，不提供修改正式 LabResult 的接口。
