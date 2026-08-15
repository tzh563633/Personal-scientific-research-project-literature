# P0 验收记录

## 真实测试素材

测试目录：

`D:\360MoveData\Users\lenovo\Desktop\7月\8文献综述\区域数字韧性`

目录清单统计为 16 个 PDF、1 个 RIS 和 1 个 DOCX。原始目录在测试期间未被写入。

## 已完成验证

- 本轮使用目录中的 10 篇 PDF 和 1 个 DOCX 完成真实上传；11/11 个 Celery 文献任务为 `succeeded`，均生成 original、TXT、Markdown 和引用 JSON 文件。
- 中文 PDF 的 GBK/Latin-1 字体映射已修复；标题抽检可得到“城市何以更加‘韧性’——数字经济的赋能效应”等论文题名，不再误取封面字段或摘要句子。
- 容器级真实 PDF 回归：`成长型矿业城市韧性综合评价研究_代大为.pdf` 解析出 211 条参考文献；DOCX 转换和回退解析生成 117 条参考文献。
- 精确 SHA-256 重复上传会直接返回已完成任务，不重复保存原文件。
- Excel 已验证隐藏元数据页、人工可见值保护、超长单元格截断和控制字符清理；平台字段更新后人工标题仍保留，数据库记录 `manual_edits`。
- 5 个模拟 RSS 源新增 5 条期刊项，关键词匹配 4 条，生成 4 条站内通知，Mailpit 收到 4 封邮件。
- Agent 队列已验证：注册、心跳、领取、白名单执行、结果回传和历史状态更新；`update excel` 与 `backup` 成功，任意 PowerShell 指令被拒绝。
- 综述任务成功生成 2 份输出；最新输出审计到 44 条来源，44 条已核实，14 条有全文，并生成缺失全文 Markdown 提醒。
- PostgreSQL 16 客户端已固定进 backend、worker、beat 镜像。新备份包含 `database.dump` 和 `storage.zip`，storage 恢复得到 57 个文件；临时数据库恢复成功，记录数为 papers=13、review_sources=86、paper_files=52。
- 系统配置测试密钥以 120 字符密文落库，明文未出现，随后已清除；管理员配置更新产生 2 条审计日志。宿主机 `scripts/backup.ps1` 已兼容 Windows PowerShell，并验证不会打包 `backups/` 或运行中 `logs/`。
- Docker Compose 服务、Alembic `0003_files_review_sources` 迁移、前端生产构建和 Mailpit 均已验证。

## 自动化结果

- `pytest -q`: 13 passed
- `python -m compileall -q backend agent tests`: passed
- `docker compose config --quiet`: passed
- 前端 `npm run build`: passed

## 当前边界

- OCR 需要额外安装 PaddleOCR 并将 `OCR_ENABLED=true`。
- GROBID 已提供可选 Compose profile，默认仍使用 PyMuPDF。
- 当前引用映射主要支持数字型 `[1]` 引用；作者-年份引用仍是后续增强项。
- 真实模型、真实 SMTP 和公网学术源密钥需要在系统配置中另行填写。
- 首版局域网访问仍使用 HTTP，只适用于可信局域网，不应暴露公网。
