# 🌍 智能旅游规划 Agent（Dify）

基于 Dify 平台构建的多工具协作 Agent，自动查询天气 + 检索景点知识库，通过 CoT 思维链生成个性化行程规划。

## 核心能力
- **Agent 工具调用**：自动调用天气 API 获取目的地未来天气
- **RAG 知识库**：10 城市景点结构化知识库（室内/室外/时长/交通/预约信息）
- **CoT 思维链**：分步规划（天气筛选 → 地理聚类 → 时间分配 → 穿衣提醒）
- **结构化 Prompt**：强制输出格式统一（行程/穿衣/提醒），Few-shot 示例稳定风格
- **幻觉控制**：自检节点确保不编造景点，天气数据与工具返回一致
- **边界处理**：知识库未收录城市主动告知，雨天自动优先室内景点

## 技术栈
- Dify（Agent 编排、知识库、自定义工具）
- FastAPI（天气插件 API 封装）
- Docker（Dify 私有化部署）

## 项目结构
travel-agent-dify/
├── README.md
├── knowledge-base/          # 10城市景点数据
├── prompts/
│   └── system-prompt.md     # 完整 System Prompt
├── tools/
│   └── weather-api/         # FastAPI 天气插件
└── screenshots/             # 演示截图
