# Bug定位Agent框架

基于知识图谱和LLM的C代码Bug定位框架

## 🎯 功能特性

- **日志解析**: 从错误日志中提取结构化信息
- **实体定位**: 在知识图谱中定位相关函数
- **调用链追踪**: 构建从入口到错误点的完整调用链
- **断点修复**: 分层降级策略修复调用链断点
  - 第1层: 图谱直接查询 (90%情况)
  - 第2层: 专家规则 (9%情况) - 异步调用、函数指针等
  - 第3层: LLM兜底 (1%情况) - 处理未知模式

## 📁 项目结构

```
bug_localization_agent/
├── config/                 # 配置模块
├── data/                   # 数据层（图谱接口）
├── agents/                 # Agent层
│   ├── log_parser_agent.py         # 日志解析
│   ├── entity_locator_agent.py     # 实体定位
│   └── chain_tracer_agent.py       # 调用链追踪
├── coordinator/            # 协调层
│   └── master_coordinator.py       # 主协调器
├── utils/                  # 工具函数
├── tests/                  # 测试
├── examples/               # 示例
└── output/                 # 输出结果
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /data/xuao/code_kg_search/bug_localization_agent

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境

复制 `.env.example` 为 `.env` 并填入配置:

```bash
cp .env.example .env
vim .env  # 或用其他编辑器
```

配置内容:
```bash
# Neo4j配置（必须）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Anthropic API（可选，用于LLM兜底）
ANTHROPIC_API_KEY=your_api_key
```

### 3. 测试连接

```bash
python tests/test_connections.py
```

预期输出:
```
✓ 项目结构存在
✓ Neo4j连接成功
✓ Anthropic API连接成功（或⚠ 未配置）
```

### 4. 运行示例

```bash
# 运行甲方MMC案例
python examples/run_mmc_case.py

# 运行自定义日志
python examples/run_mmc_case.py path/to/your/log.txt
```

## 📖 使用方法

### 方式1: 使用协调器（推荐）

```python
from coordinator.master_coordinator import MasterCoordinator

# 创建协调器
coordinator = MasterCoordinator()

# 处理日志
error_log = """
mmc0: tuning execution failed: -1
mmc0: error -1 whilst initialising MMC card
"""

result = coordinator.process(error_log)

# 查看结果
print(f"成功: {result['success']}")
print(f"调用链长度: {result['chain']['length']}")
print(f"路径: {result['chain']['path']}")

coordinator.close()
```

### 方式2: 指定起点和终点

```python
result = coordinator.process_with_specific_functions(
    error_log,
    start_func='dw_mci_pltfm_probe',
    end_func='dw_mci_execute_tuning'
)
```

### 方式3: 单独使用Agent

```python
from data.kg_interface import create_kg_interface
from agents.log_parser_agent import LogParserAgent
from agents.entity_locator_agent import EntityLocatorAgent
from agents.chain_tracer_agent import CallChainTracerAgent

# 创建图谱接口
kg = create_kg_interface()

# 使用各个Agent
log_parser = LogParserAgent()
entity_locator = EntityLocatorAgent(kg)
chain_tracer = CallChainTracerAgent(kg)

# 执行分析
parsed = log_parser.execute(error_log)
entities = entity_locator.execute(parsed)
chain = chain_tracer.execute(entities['start_entity'], entities['end_entity'])

kg.close()
```

## 🔧 图谱接口API

### 基础查询

```python
# 查找函数
func = kg.find_function('dw_mci_probe')

# 检查调用关系
has_call = kg.has_direct_call('func_a', 'func_b')

# 查找调用路径
path = kg.find_call_path('start_func', 'end_func', max_depth=10)
```

### 断点修复查询

```python
# 检查异步调用模式
async_bridge = kg.check_async_pattern('func_a', 'func_b')

# 检查函数指针模式
fp_bridge = kg.check_function_pointer_pattern('func_a', 'func_b')
```

### 上下文查询

```python
# 获取函数完整上下文
context = kg.get_function_context('dw_mci_probe')
# 包含: info, code, callers, callees, variables, related_structs
```

## 📊 输出格式

分析结果JSON格式:

```json
{
  "success": true,
  "parsed_log": {
    "error_messages": ["tuning execution failed: -1"],
    "functions": ["dw_mci_execute_tuning"],
    "inferred_entry": "dw_mci_pltfm_probe",
    "inferred_error_point": "dw_mci_execute_tuning"
  },
  "entities": {
    "start_entity": {"name": "dw_mci_pltfm_probe", "file": "..."},
    "end_entity": {"name": "dw_mci_execute_tuning", "file": "..."}
  },
  "chain": {
    "path": ["func1", "func2", "func3", ...],
    "length": 8,
    "breaks": [
      {
        "position": 2,
        "from": "func2",
        "to": "func3",
        "fixed": true,
        "method": "rule",
        "bridge": {"bridge_type": "async", ...}
      }
    ],
    "stats": {
      "total_breaks": 2,
      "fixed_by_rules": 2,
      "fixed_by_llm": 0,
      "unfixed": 0
    }
  }
}
```

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_connections.py
pytest tests/test_agents.py

# 带覆盖率
pytest --cov=. tests/
```

## 📝 开发计划

### ✅ MVP版本 (已完成)
- [x] 项目结构
- [x] 图谱接口
- [x] 日志解析Agent
- [x] 实体定位Agent
- [x] 调用链追踪Agent（含断点修复）
- [x] 主协调器
- [x] 示例脚本

### 🚧 V1.0 (进行中)
- [ ] 更多专家规则（回调、事件等）
- [ ] LLM集成（需要Anthropic API key）
- [ ] 性能优化
- [ ] 更多测试用例

### 📅 V2.0 (计划中)
- [ ] 根因分析Agent
- [ ] 修复建议Agent
- [ ] Web界面
- [ ] 历史案例库

## ⚙️ 配置说明

### 必需配置

- `NEO4J_URI`: Neo4j数据库地址
- `NEO4J_USER`: Neo4j用户名
- `NEO4J_PASSWORD`: Neo4j密码

### 可选配置

- `ANTHROPIC_API_KEY`: Claude API密钥（用于LLM兜底）
- `LLM_CONFIDENCE_THRESHOLD`: LLM置信度阈值（默认0.6）
- `MAX_CHAIN_DEPTH`: 最大搜索深度（默认15）
- `LOG_LEVEL`: 日志级别（默认INFO）

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可

MIT License

## 📞 联系

如有问题，请联系项目维护者。
