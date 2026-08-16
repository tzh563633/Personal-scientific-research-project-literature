# P4 最终验收报告

## 1. 阶段结论

P4 已完成。当前版本把原有功能模块重组为科研控制台，并完成了桌面入口、控制台首页、四个核心页面路由、后端概览聚合接口和本地启动链路。

P4 的范围是产品骨架和工作流入口，不提前承诺 P5/P6/P7 的深度能力。PDF 批量解析、DeepSeek 综述生成闭环、完整研究资产 CRUD 和最终全链路验收继续由后续阶段承接。

## 2. 已交付内容

### 2.1 控制台与后端

- 新增 `GET /api/v1/dashboard/overview`，返回文献、期刊、提醒、综述、代码项目、Agent、任务和 Excel 状态。
- 首页展示四个科研工作流入口、核心指标、最近材料和系统状态。
- 所有控制台数据继续通过已登录用户鉴权，不在响应中返回 API Key 或其他密钥。
- 保留旧路由，并将 `/journals`、`/papers`、`/reviews`、`/code` 重定向到新的产品页面。

### 2.2 四个核心页面

| 页面 | 路由 | P4 交付范围 |
| --- | --- | --- |
| 期刊追踪 | `/journal-tracking` | 复用现有期刊、关键词和监控入口 |
| 文献分析 | `/folder-analysis` | 复用现有文献上传、解析状态和 Excel 下载入口 |
| 综述撰写 | `/review-writing` | 增加 DeepSeek API Key 顶部入口，保留框架和输出入口 |
| 研究资产 | `/research-assets` | 复用代码项目、Git 状态、依赖和安全审计工作台 |

### 2.3 本地化部署入口

- `scripts/start-platform.ps1`：启动或复用 Docker Compose 服务，等待健康检查并打开浏览器。
- `scripts/create-desktop-shortcut.ps1`：在 Windows 桌面生成 `科研控制平台.lnk`。
- 已在本机桌面创建并核验快捷方式：
  - 目标程序：`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`
  - 启动参数：指向仓库内 `scripts/start-platform.ps1`
  - 工作目录：当前项目根目录

## 3. 验收标准与结果

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| 桌面快捷方式创建 | 通过 | 桌面存在 `科研控制平台.lnk`，目标和参数已读取核验 |
| 启动器重复启动 | 通过 | `start-platform.ps1 -SkipBuild -SkipAgent` 退出码为 `0` |
| 服务健康检查 | 通过 | `/health` 返回 `{"status":"ok"}` |
| 初始化状态接口 | 通过 | `/api/v1/setup/status` 返回 `initialized: true` |
| 控制台聚合接口 | 通过 | 未登录返回 `401`，一次性 JWT 访问返回 `200` |
| 四个核心路由 | 通过 | `/journal-tracking`、`/folder-analysis`、`/review-writing`、`/research-assets` 均返回 `200` |
| Docker Compose 配置 | 通过 | `docker compose config --quiet` |
| 后端测试 | 通过 | `pytest -q`：29 passed，1 个第三方兼容性警告 |
| Python 编译检查 | 通过 | `python -m compileall -q backend agent tests` |
| 前端生产构建 | 通过 | `npm run build`，仅有第三方 `#__PURE__` 与包体积非阻塞警告 |
| Git 空白检查 | 通过 | `git diff --check` |

## 4. 安全边界

- 桌面启动器只启动项目声明的 Docker Compose 服务，不接收任意命令文本。
- 宿主机 Agent 仍然只执行业务白名单任务。
- 代码项目继续只保管、查看和审计，不执行上传代码。
- P4 未增加任意本地文件夹读取能力；文件夹扫描授权链路由后续阶段实现。
- `.env`、真实 PDF、备份和运行数据不进入 Git。
- DeepSeek API Key 默认只保留在当前页面；只有用户主动勾选保存时才调用系统配置接口进行加密保存。

## 5. P4 期间发现并解决的问题

### 5.1 Windows PowerShell 5.1 中文参数编码

Windows PowerShell 5.1 对无 BOM UTF-8 脚本中的中文默认参数存在兼容性问题，第一次创建出的快捷方式名称出现乱码。

解决方案是让脚本通过 Unicode 码点构造“科研控制平台”名称，避免依赖脚本文件编码；随后删除本次生成的错误快捷方式并重新创建、读取核验。

### 5.2 嵌套 PowerShell 把 Docker stderr 误判为失败

启动器最初通过嵌套 `powershell.exe` 调用部署脚本，并使用 `*>>` 合并输出。Docker Compose 将正常状态信息写入 stderr 时，Windows PowerShell 的 `ErrorActionPreference = Stop` 将其转成异常，导致部署实际成功但启动器误报失败。

解决方案是改为在同一 PowerShell 进程中直接调用 `deploy-local.ps1`，使用参数哈希表传递开关；修复后真实启动器运行通过，退出码为 `0`。

### 5.3 验收命令使用了 PowerShell 7 专属参数

第一次运行 HTTP 鉴权检查时使用了 `Invoke-WebRequest -SkipHttpErrorCheck`，该参数在 Windows PowerShell 5.1 中不可用，导致验收命令自身失败。

解决方案是改用 `curl.exe -s -o NUL -w "%{http_code}"` 获取未登录状态码，并继续使用 `Invoke-RestMethod` 检查登录后的 JSON 响应。修复后未登录返回 `401`，已登录控制台概览返回 `200`。

## 6. 工具环境说明

本轮 in-app 浏览器自动化连接因本机 Browser 插件的 kernel assets 路径缺失而无法初始化。该问题不影响应用本身：Docker、HTTP 健康检查、OpenAPI、前端构建和后端运行时检查均已完成。视觉点击验收保留为本机工具环境的待补项，不将其伪报为已完成。

## 7. 后续阶段边界

- P5：文件夹登记与扫描、PDF 批量分析、Excel 提炼质量和任务体验。
- P6：DeepSeek API Key 到大纲、Excel、综述、引用追溯和缺失文献提醒的完整闭环。
- P7：代码分支管理、研究方法/工具/流程资产库，以及最终四页面全链路验收。

P4 完成后不自动启动 P5，后续阶段仍按用户确认流程推进。
