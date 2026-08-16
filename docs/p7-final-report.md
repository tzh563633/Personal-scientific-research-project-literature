# P7 最终验收报告

## 1. 阶段结论

P7 已完成，最终四页面所需的研究资产能力已经具备：

- 期刊追踪页面保留期刊源、关键词、最新论文和提醒；
- 文献分析页面支持 Windows 文件夹扫描、PDF 解析和 Excel；
- 综述撰写页面支持指定 Excel、模型 Key、来源追溯和缺失提醒；
- 研究资产页面支持代码安全检查、Git 分支创建、研究方法、研究工具和分析流程 CRUD；
- Windows 安装器支持点击 `Install and Run` 完成本地部署和启动。

## 2. P7 交付内容

### 2.1 Git 分支管理

- `GET /api/v1/code/projects/{id}/git/branches`
- `POST /api/v1/code/projects/{id}/git/branches`
- 分支名执行严格 ref 名称校验。
- 分支创建限制在已登记项目目录。
- 使用 `git branch` 创建引用，不检出分支、不执行项目代码。
- Git hooks 和系统级 Git 配置在变更操作中被禁用。

### 2.2 研究资产库

新增三类模型和完整 CRUD：

- `research_methods`
- `research_tools`
- `research_workflows`

研究资产页面新增：

- 研究方法标签页；
- 研究工具标签页；
- 分析流程标签页；
- 新增、编辑、删除弹窗；
- 流程步骤的逐行保存和展示。

## 3. 验收结果

| 验收项 | 结果 |
| --- | --- |
| Alembic 当前版本 | `0007_research_assets (head)` |
| Docker backend | healthy |
| Docker worker/beat/frontend | running |
| `/health` | HTTP 200 |
| `/` | HTTP 200 |
| `/journal-tracking` | HTTP 200 |
| `/folder-analysis` | HTTP 200 |
| `/review-writing` | HTTP 200 |
| `/research-assets` | HTTP 200 |
| 研究资产 API 注册 | 通过 |
| Git 分支服务测试 | 通过 |
| 研究资产 CRUD 测试 | 通过 |

当前运行数据库没有可用的代码项目，因此没有伪造运行时 Git 分支结果；自动化验收使用真实临时 Git 仓库完成了分支读取、创建和非法分支名拒绝。

## 4. 自动化结果

- `pytest -q`：37 passed，1 个 Starlette/httpx 兼容性弃用警告。
- `python -m compileall -q backend agent tests`：通过。
- `docker compose config --quiet`：通过。
- `npm run build`：通过。
- `git diff --check`：通过。
- Docker 镜像构建通过。
- `0007_research_assets` 迁移在 PostgreSQL 中成功升级。

## 5. 安全边界

- 不执行上传的 Python、PowerShell、CMD、Node 或其他项目代码。
- 分支管理只创建 Git 引用，不检出、不运行 hook。
- 研究资产只保存用户输入的文本和步骤，不自动执行流程。
- 代码项目仍使用安全解压、路径约束、依赖审计、密钥脱敏和有界预览。

## 6. 未伪报的验收限制

- 当前环境没有已登记的 Git 代码项目，因此未声称真实运行数据库中已经创建分支。
- Browser 插件的 kernel assets 路径仍无法初始化，四页面使用 HTTP 状态、生产构建、Docker 健康和 API 证据验收。
- 真实 DeepSeek 和 SMTP 仍需要用户提供真实配置后再做外部服务验收。
