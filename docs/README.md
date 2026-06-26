# 小财 - 智能资产配置顾问 Agent

## 项目概述

一个面向 C 端散户的智能资产配置 Agent，通过对话式交互采集用户画像，基于风险分层模型生成个性化资产配置方案，并提供历史压力测试验证。

## 技术架构

```
前端 (HTML + ECharts + TailwindCSS)
    ↓ HTTP API
后端 (Python FastAPI)
    ├── 对话接口 (/chat)      - KYC 对话流程
    ├── 方案接口 (/plan)      - 资产配置生成 + 压力测试
    ├── 状态机               - KYC 流程管理
    ├── 配置引擎             - 风险分层模型
    ├── 数据服务             - AKShare 金融数据
    └── LLM 客户端           - 通义千问 Qwen
```

## 已完成的功能

### 1. KYC 对话流程（状态机驱动）
- **破冰阶段**：Agent 自我介绍，自然开启对话
- **目标采集**：收集投资目标（买房/养老/教育金/财富增值）
- **风险测评**：通过情景选择题评估风险承受能力
- **资金信息**：收集可投资金额、收入支出
- **期限确认**：确认投资期限
- **方案生成**：自动调用配置引擎生成方案

### 2. 资产配置规则引擎
- **三层风险分层模型**：
  - 防御层（债券/货币基金）：稳住基本盘
  - 核心层（权益 ETF）：长期增值主力
  - 卫星层（黄金/美股/REITs）：分散风险+增强收益
- **5 种风险等级映射**：保守型 → 激进型
- **投资期限微调**：期限越长，权益比例越高
- **产品池**：9 只核心 ETF/基金，每只都有示例代码和名称

### 3. 压力测试模块
- 5 个历史极端行情情景（2008 金融危机、2015 股灾、2018 贸易战、2022 多重压力、2024 调整期）
- 组合收益 vs 沪深300 基准对比
- 展示分散化配置的保护效果

### 4. 前端界面
- **对话页面**：开始咨询 → 对话交互 → 自动推进 KYC 流程
- **配置方案页面**：指标卡片 + 饼图 + 柱状图 + 资产明细列表
- **压力测试页面**：历史情景卡片 + 损失对比 + 结论

## 项目结构

```
asset-allocation-agent/
├── backend/                    # 后端服务
│   ├── main.py                 # FastAPI 主入口
│   ├── .env                    # 环境变量（API Key）
│   ├── app/
│   │   ├── core/               # 核心模块
│   │   │   ├── config.py       # 配置管理
│   │   │   └── llm_client.py   # LLM 客户端（含 Mock 模式）
│   │   ├── models/
│   │   │   └── user_profile.py # 用户画像数据模型
│   │   ├── routers/
│   │   │   ├── chat.py         # 对话 API
│   │   │   └── plan.py         # 方案 API
│   │   └── services/
│   │       ├── state_machine.py    # KYC 状态机
│   │       ├── session_manager.py  # 会话管理
│   │       ├── allocation_engine.py # 资产配置引擎
│   │       ├── data_service.py     # 数据服务（AKShare）
│   │       └── stress_test.py      # 压力测试
│   ├── venv/                   # Python 虚拟环境
│   └── requirements.txt        # 依赖清单
├── frontend/
│   └── index.html              # 前端页面（含 CSS + JS）
├── data/                       # 数据缓存目录
└── docs/
    └── README.md               # 本文档
```

## 快速启动

### 1. 配置 API Key

编辑 `backend/.env`：

```bash
DASHSCOPE_API_KEY=你的通义千问APIKey
```

> 获取方式：访问 [阿里云百炼平台](https://bailian.console.aliyun.com/) 创建 API Key

### 2. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi uvicorn dashscope akshare numpy pandas pydantic
python main.py
```

后端启动后访问：
- API 服务：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`

### 3. 启动前端

```bash
cd frontend
python -m http.server 3000
```

前端访问：`http://localhost:3000`

### 4. 测试对话

1. 打开 `http://localhost:3000`
2. 点击"开始咨询"
3. 回答 Agent 的问题（目标、风险偏好、资金、期限）
4. 完成后切换到"配置方案"页面查看结果
5. 切换到"压力测试"页面查看历史回测

## 关键 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/chat/start?session_id=` | POST | 开始新对话 |
| `/chat/send` | POST | 发送消息 `{message, session_id}` |
| `/chat/profile/{session_id}` | GET | 查看用户画像 |
| `/plan/generate/{session_id}` | POST | 生成配置方案 |
| `/plan/stress-test/{session_id}` | GET | 压力测试 |
| `/plan/example` | GET | 示例方案（无需会话） |

## 核心设计决策回顾

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 用户群体 | C端散户 | 标准化程度高，冷启动快 |
| 交互入口 | Web H5 | 开发迭代快，无平台审核 |
| 交互方式 | 混合式（对话+表单） | 对话建立信任，表单高效采集 |
| 配置模型 | 规则化+风险分层 | 可解释性强，合规友好 |
| 产品颗粒度 | 大类+子类+示例产品 | 可执行性+合规缓冲 |
| 陪伴深度 | 半持续（再平衡提醒） | MVP性价比最优 |
| 解释方式 | 情景模拟+故事化 | 散户易理解 |
| 数据策略 | AKShare免费数据 | 零成本MVP |
| 大模型 | 通义千问Qwen | 中国市场最优选 |
| Agent框架 | 自己写工作流 | 规则驱动，更清晰可控 |

## 下一步建议

### 近期（1-2 周）
1. **填入真实 API Key** 测试 LLM 对话效果
2. **优化 Prompt**：根据实际对话效果调整各状态的系统提示词
3. **丰富资产类别**：增加更多 ETF/基金产品到产品池
4. **完善压力测试**：接入真实 AKShare 历史数据

### 中期（1-2 月）
1. **用户系统**：添加手机号/微信登录
2. **持仓记录**：让用户记录实际持仓，计算偏离度
3. **再平衡提醒**：定期检测组合 drift，推送调仓建议
4. **前端优化**：迁移到 React/Vue 框架，提升交互体验

### 长期（3-6 月）
1. **合规接入**：申请基金投顾牌照或对接持牌机构
2. **交易闭环**：对接券商/基金销售平台实现一键下单
3. **AI 增强**：接入更多数据源（宏观指标、舆情），提升配置精准度
4. **B 端输出**：将 Agent 能力封装为 API，赋能中小金融机构

## Mock 模式说明

在没有配置 API Key 的情况下，系统会自动进入 Mock 模式：
- LLM 客户端返回预设回复
- 可完整测试 KYC 流程和状态流转
- 配置引擎和压力测试正常工作

Mock 模式下的预设回复覆盖所有 KYC 状态，可用于前端开发和流程验证。

## 注意事项

1. **合规风险**：当前版本为投资辅助工具，不构成投资建议。涉及具体产品推荐需申请相应牌照。
2. **数据延迟**：AKShare 免费数据可能有延迟，生产环境建议购买付费数据服务。
3. **内存存储**：MVP 阶段会话数据存储在内存中，服务重启后数据丢失。生产环境需接入 Redis/数据库。
4. **安全风险**：`.env` 文件中的 API Key 不要提交到代码仓库，生产环境使用密钥管理服务。

## 联系方式

如有问题或建议，欢迎交流！
