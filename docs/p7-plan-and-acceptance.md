# P7 计划与验收标准

## 1. P7 目标

P7 负责完成最终目标中的“研究资产”页面：

1. 查看和管理已上传代码项目的 Git 分支。
2. 保存研究方法、研究工具和分析流程。
3. 让这些资产可编辑、删除和复用。
4. 保持“平台不执行上传代码”的安全边界。

## 2. 实施范围

### 2.1 Git 分支

- `GET /api/v1/code/projects/{id}/git/branches`
- `POST /api/v1/code/projects/{id}/git/branches`
- 分支名必须通过安全校验。
- 创建操作只在项目存储目录内执行 `git branch`，不检出分支、不运行上传项目代码。
- Git hooks 被禁用，系统级 Git 配置不参与操作。

### 2.2 研究资产库

- `research_methods`：方法名称、说明、适用场景、步骤、优势、局限和关联对象。
- `research_tools`：工具名称、用途、安装方式、使用说明、注意事项和关联项目。
- `research_workflows`：流程名称、说明和步骤列表。
- 三类资产均提供列表、创建、更新和删除接口。
- 研究资产页面提供对应标签页和编辑弹窗。

## 3. 验收标准

### 3.1 自动化验收

- `pytest -q` 通过，包含真实临时 Git 仓库分支创建和资产 CRUD。
- `python -m compileall -q backend agent tests` 通过。
- `docker compose config --quiet` 通过。
- `npm run build` 通过。
- Alembic `0007_research_assets` 可升级现有数据库。

### 3.2 功能验收

1. 上传或登记一个包含 `.git` 的代码项目。
2. 研究资产页面可以查看当前分支和已有分支。
3. 输入合法分支名后可以创建分支。
4. 输入目录穿越、空格或非法 ref 名称时被拒绝。
5. 新增、编辑、删除研究方法。
6. 新增、编辑、删除研究工具。
7. 新增、编辑、删除分析流程。
8. 页面刷新后资产仍从数据库恢复。
9. 资产操作不会执行项目中的 Python、PowerShell、Node 或其他代码。

## 4. 最终四页面验收

- 期刊追踪：期刊源、关键词、最新条目、提醒和抓取状态可见。
- 文献分析：指定文件夹扫描、PDF 解析、Excel 输出和人工保护可用。
- 综述撰写：DeepSeek Key、指定 Excel、大纲、来源追溯和缺失提醒可用。
- 研究资产：Git 分支、代码安全检查、方法、工具和流程库可用。
- Windows 安装器：点击 `Install and Run` 后完成本地部署并打开控制平台。

## 5. 交付物

- `backend/migrations/versions/0007_research_assets.py`
- Git 分支 API 和安全操作服务
- 研究资产 CRUD API
- `frontend/src/views/Code.vue` 研究资产工作台
- P7 自动化测试
- `docs/p7-final-report.md`
