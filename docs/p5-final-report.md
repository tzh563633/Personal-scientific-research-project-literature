# P5 最终验收报告

## 1. 阶段结论

P5 已完成。

本阶段把 P4 的控制台骨架推进为可实际使用的本地科研材料工作流，完成了：

- Windows 本地文件夹登记、宿主 Agent 白名单扫描和 PDF 批量导入；
- SHA-256 去重、异步 PDF 解析、TXT/Markdown 输出和解析状态追踪；
- Excel 更新历史、人工修改保护和期刊监控结果展示；
- Windows 图形安装器，支持点击“Install and Run”完成复制、初始化、启动和浏览器打开；
- 安装器、文件夹扫描、期刊和 Excel 相关的自动化测试与部署文档。

P5 完成后不自动进入下一阶段。

## 2. 交付内容

### 2.1 文件夹文献分析

- 新增 `paper_folders`、`folder_documents` 数据表。
- 新增 `/api/v1/folders` 文件夹登记、文档查询和扫描接口。
- 文件夹路径必须是绝对 Windows 路径，文件相对路径会拒绝盘符、绝对路径、空路径和 `..` 越界。
- 宿主 Agent 仅接受 `scan_folder` 业务任务，不执行任意 PowerShell、CMD 或 shell 文本。
- 扫描仅处理 PDF，记录相对路径、文件名、大小、修改时间和 SHA-256。
- 通过 SHA-256 和已有 `PaperFile` 记录进行跨文件夹去重。
- 新导入文件进入现有异步解析流程，并生成原文件、TXT、Markdown 和引用 JSON。

### 2.2 期刊和 Excel 体验

- 期刊页面显示最近抓取时间、抓取结果、新增条目、关键词命中和错误信息。
- 期刊页面增加站内提醒和手动监控入口。
- Excel 页面增加更新历史、论文数量和人工保留数量。
- Excel 定时更新继续基于隐藏元数据页和人工修改快照，平台刷新不会覆盖人工可见修改。

### 2.3 Windows 一键安装和运行

- 双击 `installer\Install-ResearchPlatform.cmd` 可打开 Windows 安装窗口。
- 点击 `Install and Run` 后，安装器会：
  1. 检查 Docker CLI 和 Docker Desktop；
  2. 在 Docker 不可用且 `winget` 可用时尝试安装 Docker Desktop；
  3. 等待 Docker 引擎就绪；
  4. 将项目复制到 `%LOCALAPPDATA%\ResearchControlPlatform`；
  5. 排除 `.git`、`.env`、`storage`、`node_modules` 和构建缓存；
  6. 生成本机随机密钥并启动 Docker Compose；
  7. 创建桌面“科研控制平台”快捷方式；
  8. 启动宿主 Agent、等待健康检查并打开浏览器。
- 安装器不使用 `/MIR`，不会清空目标目录中未被安装器管理的文件。
- 安装日志写入 `%LOCALAPPDATA%\ResearchControlPlatformLogs\installer.log`。
- Docker Desktop 需要重启或管理员确认时，安装器会明确报告失败原因，不伪报成功。

## 3. 真实验收

### 3.1 测试素材

真实测试目录：

`D:\360MoveData\Users\lenovo\Desktop\7月\8文献综述\区域数字韧性`

目录中实际包含 16 个 PDF、1 个 RIS 和 1 个 DOCX。扫描任务只读取 PDF，不处理 RIS、DOCX 或其他文件。

### 3.2 文件夹扫描结果

| 验收项 | 结果 |
| --- | --- |
| 中文 Windows 路径登记 | 通过 |
| 识别 PDF 数量 | 16 |
| 扫描任务 | `succeeded` |
| 新导入 PDF | 6 |
| SHA-256 去重 PDF | 10 |
| 文件夹文档记录 | 16 |
| 异步解析完成 | 16/16 |
| TXT 输出 | 16/16 |
| Markdown 输出 | 16/16 |
| 扫描错误 | 0 |

源文件夹中的 PDF 没有被移动、改名或覆盖，平台只将文件上传到自身存储目录进行解析。

### 3.3 自动化回归结果

- `pytest -q`：34 passed，1 个 Starlette/httpx 兼容性弃用警告。
- `python -m compileall -q backend agent tests`：通过。
- `docker compose config --quiet`：通过。
- `npm run build`：通过。
- `git diff --check`：通过。
- `installer\Install-ResearchPlatform.ps1 -TestOnly`：通过。
- 安装器测试确认存在 `Install and Run` 按钮、Agent 启动入口和非破坏性复制策略。

前端构建仅保留第三方 `#__PURE__` 注释和 chunk 体积提示，不影响构建产物。

## 4. P5 期间发现并解决的问题

### 4.1 Alembic 版本号超过数据库字段长度

新增迁移最初使用了过长的 revision id，超过 `alembic_version.version_num` 的 32 字符限制，导致容器启动迁移失败。

解决方案是将 revision id 缩短为 `0005_folder_scan_install`，保留迁移语义并符合数据库字段约束。修复后 Docker Compose 可以完成迁移并启动后端。

### 4.2 中文 Windows 路径在验收命令中被写成问号

第一次文件夹验收失败，错误显示 `Registered folder does not exist`。检查发现 D 盘目录真实存在且包含 16 个 PDF，但数据库中此前登记的路径已经变成问号字符。

排查后确认问题来自测试命令的 PowerShell/容器参数编码，不是 Agent 的路径解析逻辑。重新使用 UTF-8 JSON 请求登记原始路径后，数据库保留了完整中文路径，Agent 成功读取并完成扫描。

选择 UTF-8 请求而不是在 Agent 中增加模糊路径猜测，是因为路径必须精确且可审计；猜测或替换问号可能把任务指向错误目录。

### 4.3 一键安装需要处理 Docker 未就绪

Windows 新机器可能没有 Docker CLI、Docker Desktop 尚未启动，或者 Docker Desktop 安装后需要重启。

解决方案是安装器集中处理 Docker 检测、`winget` 最佳努力安装、就绪轮询、明确错误提示和安装日志。这样用户只需点击安装按钮，仍能在外部依赖缺失时得到可操作的失败信息，不会看到“安装成功但平台打不开”的假状态。

### 4.4 安装复制不能破坏目标目录

本地安装需要复制完整项目，但目标目录可能已经存在用户文件。使用镜像同步命令会有误删风险。

解决方案是使用 `robocopy /E`，明确排除运行数据和缓存，并禁止 `/MIR`。安装器只补充或覆盖安装器管理的项目文件，不主动删除目标目录中的其他内容。

### 4.5 Windows PowerShell 下前端构建受到子进程权限限制

普通受限执行环境中，Vite 启动 esbuild 时出现 `spawn EPERM`。同一代码在 Docker 构建和授权本机权限下均可成功编译。

这属于验收环境的子进程权限问题，不是前端源码错误。最终使用已授权的本机权限完成生产构建，并保留非阻塞第三方警告。

## 5. 当前边界

- Docker Desktop 仍是 Windows 本地运行时依赖；安装器只能在 `winget` 可用时尝试自动安装。
- 首次安装后仍需要在浏览器中完成管理员初始化。
- 宿主 Agent 需要 Python 3.11 或更新版本；安装脚本会自动安装缺失的 `httpx` 依赖。
- OCR 和 GROBID 仍是可选能力，不作为默认 P5 依赖。
- 局域网访问继续限定在可信网络，未配置公网 HTTPS 反向代理。
- 本机 Browser 插件的 kernel assets 路径异常，视觉点击验收工具未能初始化；本阶段使用 HTTP、API、容器健康、真实文件夹扫描和生产构建完成可复核验收。

## 6. 交付文件

- `installer\Install-ResearchPlatform.cmd`
- `installer\Install-ResearchPlatform.ps1`
- `docs\p5-plan-and-acceptance.md`
- `docs\p5-final-report.md`
- `backend\app\routers\folders.py`
- `backend\app\services\folders.py`
- `agent\folder_scan.py`
- `backend\migrations\versions\0005_folder_scan_install_experience.py`
- `tests\test_folder_scan.py`

外部《科研项目开发过程bug和问题.md》继续保存在用户指定的 D 盘目录，不纳入 GitHub 交付。
