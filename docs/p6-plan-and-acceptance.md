# P6 计划与验收标准

## 1. P6 目标

P6 负责把“综述撰写”页面从框架入口推进为可追溯的生成闭环：

1. 用户在页面顶部输入 DeepSeek API Key。
2. 用户选择平台内的指定 Excel 文献表。
3. 用户填写综述名称和大纲。
4. 平台按 Excel 中的 `paper_id` 回查已入库文献，并补充关键词检索和公开学术源。
5. 生成任务输出 Markdown 综述、来源清单、事实核查摘要和缺失全文提醒。

真实模型调用失败时，平台降级到可重复的 Mock Provider，不阻塞本地自动化验收。

## 2. 实施范围

### 2.1 Excel 输入

- 新增 `GET /api/v1/excel/files`，只列出平台 `storage/exports` 下的 `.xlsx`/`.xlsm`。
- 综述框架保存 `excel_path`，路径必须是 `exports/` 下的相对路径。
- 禁止通过综述接口读取任意绝对路径、目录穿越路径或平台存储目录以外的文件。

### 2.2 模型密钥

- 页面顶部保留 DeepSeek API Key 输入。
- 勾选保存时写入现有加密系统配置。
- 不勾选保存时，Key 只通过当前生成请求使用，不写入 Job、日志或 ReviewFramework。
- 异步任务优先读取加密保存的 DeepSeek Key；没有 Key 时使用 Mock Provider。

### 2.3 综述生成

- Excel 选中的 `paper_id` 优先作为来源。
- 来源统一记录 `source_type`、核实状态、全文状态、DOI 和元数据。
- 公开学术源继续使用 OpenAlex、Crossref、Semantic Scholar 的受限查询。
- 生成结果记录来源数量、已核实数量、全文数量和事实核查摘要。
- 未核实来源或未下载全文的来源进入缺失文献 Markdown。

## 3. 验收标准

### 3.1 自动化验收

- `pytest -q` 通过，包含 Excel 指定来源和临时 DeepSeek Key 不落库测试。
- `python -m compileall -q backend agent tests` 通过。
- `docker compose config --quiet` 通过。
- `npm run build` 通过。
- Alembic `0006_review_excel_inputs` 可升级现有数据库。

### 3.2 功能验收

1. 创建一个包含平台 `paper_id` 的 Excel。
2. 在综述页面选择该 Excel，填写大纲并保存框架。
3. 使用 Mock Provider 生成综述。
4. 生成结果必须包含已选 Excel 文献来源。
5. 来源抽屉可以查看标题、来源类型、核实状态、全文状态和 DOI。
6. 生成结果必须包含缺失全文提醒路径和事实核查摘要。
7. 输入临时 DeepSeek Key 后，生成任务可以使用该 Key，但数据库不出现明文 Key。
8. 使用无效 Excel 路径时，任务失败并返回结构化错误。

## 4. 不在 P6 范围内

- 不承诺真实 DeepSeek 模型的学术事实准确率。
- 不自动登录知网、Google Scholar 或其他需要账号的来源。
- 不把 Excel 解析扩展成任意办公文件执行。
- 不开放公网部署、多人协作和复杂权限隔离。

## 5. 交付物

- `backend/migrations/versions/0006_review_excel_inputs.py`
- 综述 Excel 输入、来源追溯和模型 Key 使用逻辑
- `frontend/src/views/Reviews.vue`
- P6 单元测试和 API 契约更新
- `docs/p6-final-report.md`
