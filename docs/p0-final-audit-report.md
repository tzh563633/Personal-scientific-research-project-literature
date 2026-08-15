# 科研数据平台 P0 最终审计与验收报告

## 结论

P0 目标已完成并通过本地化部署验收。平台可在 Windows + Docker Desktop
环境中一键启动，核心文献、Excel、期刊、Agent、综述、备份恢复和安全边界
均已实现；P0 当前状态为 **通过**。

本报告完成后，项目进入 P1：Git 深度管理和依赖分析扩展。P1 第一批交付
已完成，记录见 `docs/p1-progress.md`。

## 验收范围

- 真实材料目录：`D:\360MoveData\Users\lenovo\Desktop\7月\8文献综述\区域数字韧性`
- 目录材料：16 个 PDF、1 个 RIS、1 个 DOCX
- 本轮处理：10 个 PDF 和 1 个 DOCX，11/11 个文献处理任务成功
- 原始测试目录未被平台写入

## 自动化检查

| 检查项 | 结果 |
| --- | --- |
| `pytest -q` | 15 passed |
| `python -m compileall -q backend agent tests` | passed |
| `docker compose config --quiet` | passed |
| 前端 `npm run build` | passed |
| Docker 前端镜像构建 | passed |
| Alembic 当前版本 | `0004_revoked_tokens` |
| Compose 服务健康 | PostgreSQL、Redis、backend、worker、beat、frontend、Mailpit 均运行 |

前端构建仅有非阻塞的 bundle 体积和第三方注释警告，不影响产物生成。

## 功能验收

### 文献与解析

- 中文 PDF 的 GBK/Latin-1 字体映射已修复。
- 典型标题可正确提取，包括成长型矿业城市韧性、数字经济赋能城市韧性、
  数智韧性和数字孪生提升城市韧性等论文。
- PDF 参考文献示例解析 211 条，DOCX 参考文献解析 117 条。
- TXT、Markdown、JSON 输出均已生成。
- SHA-256 重复文件上传会跳过重复保存并返回已完成任务。
- OCR 和 GROBID 保留为可选能力，默认使用 PyMuPDF。

### Excel 与数据保护

- Excel 包含隐藏 `_meta` 元数据页。
- 人工修改快照能够阻止定时更新覆盖人工值。
- 数据库中已记录 `manual_edits=1`。
- 超长单元格和控制字符清理已覆盖。

### 期刊、通知和邮件

- 5 个模拟 RSS 源完成抓取。
- 新增期刊项 5 条，关键词命中 4 条，站内提醒 4 条。
- Mailpit 收到 4 封通知邮件。

### Agent 与安全边界

- Agent 注册、心跳、领取任务、执行结果回传均已验证。
- `update_excel` 和 `backup` 业务任务可执行。
- 任意 PowerShell 文本被业务白名单拒绝。
- 伪造 `powershell` Agent 任务返回 `ok=false`。
- Agent 不执行上传代码，代码仅保存、解压、查看和记录。
- 管理员 JWT 登出后再次访问受保护接口返回 `401`，服务端吊销令牌生效。

### 综述与来源审计

- 最新综述输出审计到 44 条来源，44 条已核实，14 条有全文。
- 未下载全文的来源进入缺失全文 Markdown 提醒文件。
- `ReviewSource` 表记录来源类型、核实状态、全文状态和元数据。

## 本地化部署验收

新增并验证：

- `scripts/deploy-local.ps1`
- `scripts/status-local.ps1`
- `scripts/stop-local.ps1`
- `scripts/start-agent.ps1` 的依赖检查与安装流程
- backend Docker healthcheck
- `docs/local-deployment.md`

`deploy-local.ps1 -SkipBuild` 已在宿主机权限下完整运行，执行结果包括：

- 访问 `http://localhost:80` 返回 200
- 访问实际 LAN 地址返回 200
- `/health` 返回 `ok`
- `/api/v1/setup/status` 可访问
- 自动等待 PostgreSQL 迁移和 backend 健康状态
- 输出 Web、Mailpit、LAN 和 Agent 启动入口

手机访问要求与电脑处于同一可信局域网；backend 和 Mailpit 仍只绑定
localhost，避免直接暴露内部接口。

## 性能与恢复

- 连续 50 次 `/health` 请求全部成功，平均约 58.31 ms。
- 最新备份目录包含 `database.dump` 和 `storage.zip`。
- storage 临时恢复得到 57 个文件，Excel 和解析 TXT 均存在，未恢复
  `backups/` 递归目录。
- 数据库 dump 已恢复到独立临时 PostgreSQL 数据库，统计为：
  `papers=13`、`review_sources=86`、`paper_files=52`。

## 当前数据统计

| 表或产物 | 数量 |
| --- | ---: |
| papers | 13 |
| paper_files | 52 |
| succeeded jobs | 64 |
| alerts | 4 |
| notifications | 8 |
| review_sources | 86 |
| manual_edits | 1 |
| parsed 文件 | 39 |
| review 文件 | 1 |

## 已知边界

1. OCR、GROBID、真实大模型和真实 SMTP 需要额外安装或配置密钥后再做真实环境验收。
2. 当前引用映射以数字引用 `[1]` 为主，作者-年份映射列入 P1 扩展。
3. 首版局域网部署使用 HTTP，不应直接暴露到公网。
4. 前端生产 bundle 较大，已通过构建但可在 P1 做代码分割优化。
5. 宿主 Agent 需要在 Windows 上单独启动，不由 Compose 自动托管。

## 审计结论

没有发现阻断 P0 交付的高危问题。P0 目标完成，平台可作为个人科研数据平台
在可信 Windows 局域网中本地运行。P1 已开启，优先实现只读 Git 状态/提交记录
和不执行代码的依赖清单分析接口。
