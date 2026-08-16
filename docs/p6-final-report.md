# P6 最终验收报告

## 1. 阶段结论

P6 已完成。

本阶段把综述撰写页面从“框架和模型入口”补成可追溯的生成闭环：

- 可选择平台 `storage/exports` 下的指定 Excel；
- Excel 中的 `paper_id` 会优先回查平台文献；
- 生成结果记录来源、核实状态、全文状态和事实核查摘要；
- DeepSeek Key 支持当前请求临时使用或加密保存；
- 临时 Key 不进入 Job、框架表或日志；
- 真实模型失败时自动降级到 Mock Provider；
- 输出缺失全文 Markdown 提醒和来源查看抽屉。

## 2. 主要实现

### 2.1 指定 Excel

- 新增 `GET /api/v1/excel/files`，只返回平台 `storage/exports` 下的 `.xlsx`/`.xlsm`。
- `ReviewFramework.excel_path` 保存相对路径，不接受绝对路径和目录穿越。
- Excel 中的 `paper_id` 作为平台文献对象索引，避免把同一文献再次复制成外部来源。

### 2.2 模型 Key

- 页面顶部保留 DeepSeek API Key。
- 勾选保存时使用现有加密系统配置。
- 不勾选保存时，Key 仅通过当前生成请求传入同步生成路径，不写入数据库。
- 异步 Worker 会读取加密保存的 Key；没有 Key 时使用 Mock Provider。

### 2.3 来源和事实核查

- `ReviewOutput` 增加来源数量、已核实来源数量、全文来源数量和事实核查摘要。
- `ReviewSource` 记录 `source_type`、DOI、核实状态、全文状态和来源元数据。
- `/reviews/outputs/{id}/sources` 可查询完整来源清单。
- 公开学术源仍通过 OpenAlex、Crossref、Semantic Scholar 搜索，并在可用时补充公开 PDF。

## 3. 真实运行验收

使用当前 Docker 平台中的 `exports/papers.xlsx`：

| 验收项 | 结果 |
| --- | --- |
| Excel 文件列表接口 | 通过 |
| 框架保存指定 Excel | 通过 |
| 异步综述任务 | `succeeded` |
| 记录来源数量 | 24 |
| 已核实来源 | 24 |
| 已有全文来源 | 19 |
| 事实核查通过 | 24/24 |
| 缺失文献提醒 | `reviews/missing-2.md` |
| 来源查询接口 | 通过 |
| Alembic 迁移 | `0006_review_excel_inputs (head)` |

本次真实运行使用 Mock Provider，未提交真实 DeepSeek API Key；真实 Key 只在用户配置后执行。

## 4. 自动化结果

- `pytest -q`：36 passed，1 个 Starlette/httpx 兼容性弃用警告。
- `python -m compileall -q backend agent tests`：通过。
- `npm run build`：通过。
- `git diff --check`：通过。
- `docker compose build backend worker beat frontend`：通过。
- Docker backend/frontend/worker/beat 重启成功。

前端构建仅有第三方 `#__PURE__` 注释和 chunk 体积提示。

## 5. 期间发现并解决的问题

### 5.1 保存的 DeepSeek Key 没有被 Worker 使用

系统设置接口已经把 Key 加密写入 `system_configs`，但原 Provider 只读取环境变量，导致页面提示“已保存”而异步任务仍使用 Mock。

解决方案是让综述服务读取并解密 `DEEPSEEK_API_KEY`，同时支持当前请求临时 Key；临时 Key 不写入 Job payload，避免敏感值进入持久化数据。

### 5.2 综述生成没有指定 Excel 输入

原框架只保存名称和文本，生成服务依赖关键词检索，用户无法指定某次 Excel 结果作为综述边界。

解决方案是给框架增加 `excel_path`，只允许 `storage/exports` 下的 Excel，并按表内 `paper_id` 回查平台文献。

### 5.3 来源可追溯但页面缺少查看入口

后端已经有 `ReviewSource`，但页面只显示综述正文和缺失提醒路径。

解决方案是在结果表中增加来源统计、事实核查摘要和来源抽屉，直接查看标题、来源类型、核实状态、全文状态和 DOI。

## 6. 当前边界

- 真实 DeepSeek 质量、事实准确率和网络可用性仍依赖用户提供真实 API Key。
- 综述页面选择的是平台内 Excel，不开放任意本地路径读取。
- 未自动登录知网、Google Scholar 等需要账号的来源。
- Browser 插件仍受本机 kernel assets 路径问题影响，视觉点击验收使用 API、Docker 和生产构建证据替代。
