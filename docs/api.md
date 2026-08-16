# API 摘要

API 前缀为 `/api/v1`，Swagger 文档位于 `/docs`。

## 初始化与认证

- `GET /setup/status`
- `POST /setup/admin`
- `POST /auth/login`
- `POST /auth/logout` (requires the current Bearer token and revokes it)

## 文献与任务

- `POST /papers/upload`
- `POST /papers/upload/batch`
- `GET /papers`
- `GET /papers/{id}`
- `PATCH /papers/{id}`
- `GET /papers/{id}/files`
- `GET /folders`
- `POST /folders`
- `PUT /folders/{id}`
- `DELETE /folders/{id}`
- `GET /folders/{id}/documents`
- `POST /folders/{id}/scan`
- `GET /jobs/{id}`
- `POST /jobs/{id}/cancel`

## 业务模块

- `/excel`
- `GET /excel/files`
- `/journals`
- `GET /journals/items`
- `GET /journals/alerts`
- `/code`
- `GET /code/projects/{id}/tree?path=...`
- `GET /code/projects/{id}/files/preview?path=...`
- `GET /code/projects/{id}/inspection-report`
- `GET /code/projects/{id}/dependencies`
- `GET /code/projects/{id}/security-audit`
- `GET /code/projects/{id}/git/status`
- `GET /code/projects/{id}/git/branches`
- `POST /code/projects/{id}/git/branches`
- `GET /code/projects/{id}/git/commits`
- `GET /code/projects/{id}/git/commits/{hash}`
- `GET /code/projects/{id}/git/diff?path=...`
- `/commands`
- `/reviews`
- `POST /reviews/frameworks` accepts an optional `excel_path` under the
  platform `storage/exports` directory.
- `POST /reviews/generate` accepts an optional `excel_path` and transient
  `deepseek_api_key`; the transient key is never stored in a job payload.
- `GET /reviews/outputs/{id}/sources`
- `/system`
- `/agent`
- `POST /agent/folders/{id}/documents` (multipart PDF upload from the host Agent)
- `GET /dashboard/overview`
- `/research-assets/methods`
- `/research-assets/tools`
- `/research-assets/workflows`
- `GET /jobs/{id}` and `POST /jobs/{id}/cancel` use the common job status
  values `pending`, `running`, `succeeded`, `failed`, and `cancelled`.

`security-audit` is read-only. It analyzes dependency versions, licenses, and
vulnerabilities. OSV querying is disabled by default; set `OSV_ENABLED=true`
to enable the optional provider. Network failures preserve local audit results
and are returned as warnings.

所有受保护接口使用 `Authorization: Bearer <JWT>`。Agent 接口使用 `X-Agent-Token`。

`POST /api/v1/commands` 只登记业务白名单任务并返回 `pending`；宿主机 Agent
领取任务后，状态才会变为 `running`、`succeeded` 或 `failed`。可通过
`GET /api/v1/commands` 查看最近指令历史，或使用 `GET /api/v1/commands/{id}` 查询单条指令。

Agent 启动时调用注册接口获得 `agent_id`，之后使用该 ID 发送心跳、领取任务和回传结果。
