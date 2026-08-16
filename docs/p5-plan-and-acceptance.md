# P5 计划与验收标准

## 1. P5 目标

P5 负责把 P4 的控制台骨架推进到可以持续使用的两条工作流：

1. 在 Windows 本地通过点击式安装器完成项目安装、服务启动和浏览器打开。
2. 在“文献分析”页面登记宿主机文件夹，由白名单 Agent 扫描其中的 PDF，并导入平台进入批量解析。
3. 在“期刊追踪”页面补充更新结果、提醒状态和监控错误的可视化。
4. 在 Excel 页面补充更新历史、人工修正保护状态和批量分析结果反馈。

## 2. P5 新增硬需求：Windows 点击式安装运行

### 2.1 用户路径

1. 用户进入项目安装目录，双击 `installer\Install-ResearchPlatform.cmd`。
2. 安装窗口显示源目录、默认安装目录、Docker 状态和安装说明。
3. 用户点击“安装并运行”按钮。
4. 安装器将项目复制到用户本地应用目录，不复制 `.git`、`.env`、运行数据和构建缓存。
5. 如果系统没有 Docker CLI，安装器优先尝试使用 Windows Package Manager 安装 Docker Desktop；失败时给出清晰的人工处理提示。
6. 安装器创建随机本地密钥、桌面快捷方式，启动 Docker Compose。
7. 安装器等待 backend health 和 setup status 成功后打开控制平台。

### 2.2 安装边界

- 安装目录默认使用 `%LOCALAPPDATA%\ResearchControlPlatform`，避免默认写入受保护的 `Program Files`。
- 安装器不上传项目文件、不读取未选择的用户目录、不把密码或 API Key 写入日志。
- Docker Desktop 是平台运行时依赖；自动安装只能作为 Windows Package Manager 可用时的最佳努力路径。
- Docker Desktop 若需要重启或管理员确认，安装器必须停止并显示原因，不能伪报安装成功。

## 3. P5 功能范围

### 3.1 文件夹文献分析

- 登记文件夹路径、显示名称和是否递归扫描。
- 通过宿主机 Agent 执行固定 `scan_folder` 任务。
- 只扫描 PDF，拒绝符号链接和越出登记根目录的路径。
- 记录文件名、相对路径、大小、修改时间、SHA-256、导入状态和解析状态。
- 重复文件不重复入库；新增文件导入后进入既有 PDF 解析 Worker。
- 页面显示扫描进度、文件清单、失败原因、重试和最新 Excel 更新。

### 3.2 期刊追踪

- 展示最近抓取时间、抓取结果、新增条目、关键词命中和错误信息。
- 支持启用/停用期刊和关键词策略的快速操作。
- 保留 RSS 优先和静态网页补充策略。

### 3.3 Excel 结果体验

- 显示 Excel 更新历史和最近一次更新状态。
- 显示新增、保留人工修改和失败原因。
- 批量解析完成后可以从文献分析页下载最新 Excel。

## 4. P5 不做的内容

- 不在 P5 完成 DeepSeek 综述生成质量的最终优化。
- 不在 P5 完成研究方法、工具和流程资产库的完整 CRUD。
- 不执行上传代码，不开放任意 PowerShell、CMD 或 shell。
- 不把平台部署为公网服务。

## 5. 验收标准

### 5.1 安装器

- 在 Windows 上双击 `installer\Install-ResearchPlatform.cmd` 可以打开安装窗口。
- 点击“安装并运行”后，安装目录存在完整运行所需文件。
- `.git`、`.env`、`storage` 运行数据和前端构建缓存不从源目录复制到安装包。
- Docker 已可用时，安装器能自动生成本地 `.env`、创建桌面快捷方式、启动 Compose 并打开浏览器。
- Docker 不可用且 `winget` 可用时，安装器尝试安装 Docker Desktop；需要重启或人工确认时必须明确提示。
- 运行完成后 `/health` 返回 `ok`，`/api/v1/setup/status` 可访问，桌面快捷方式指向安装目录。

### 5.2 文件夹扫描

- 使用测试目录
  `D:\360MoveData\Users\lenovo\Desktop\7月\8文献综述\区域数字韧性`
  登记并扫描。
- 扫描结果只包含 PDF，记录相对路径和 SHA-256。
- 重复扫描不重复创建 Paper 或 PaperFile。
- 新增 PDF 会进入既有异步解析流程，并可生成 TXT/Markdown。
- 路径越界、符号链接、非目录和不可读文件均有结构化错误。

### 5.3 工程回归

- `pytest -q`
- `python -m compileall -q backend agent tests`
- `docker compose config --quiet`
- `npm run build`
- PowerShell 两个启动脚本和安装器通过解析检查。
- Docker backend healthy，前端、健康接口、四个控制台路由可访问。

## 6. P5 交付物

- `docs/p5-plan-and-acceptance.md`
- Windows 点击式安装器和安装入口。
- 文件夹登记、Agent 扫描、批量导入 API、数据模型和迁移。
- 期刊追踪和 Excel 结果体验改造。
- 单元、集成和本地运行验收测试。
- `docs/p5-final-report.md`
- P5 问题追加到 D 盘外部复盘文档；该文档不推送 GitHub。

P5 完成后不自动进入 P6。
