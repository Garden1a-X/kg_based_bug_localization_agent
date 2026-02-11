# Bug定位Agent框架

基于知识图谱和LLM的C代码Bug定位框架，专注于从错误日志追踪到完整调用链。

## 🎯 核心功能

### 1. 端到端调用链追踪
从简单的错误日志（3行）自动推断出完整的16节点调用链，包括：
- ✅ 日志解析：从错误信息提取关键函数
- ✅ 实体定位：在知识图谱中精确定位函数
- ✅ 路径搜索：支持直接调用和间接调用（异步、函数指针）
- ✅ 断点修复：4层降级策略确保链路完整

### 2. 分层降级策略
- **第1层：扩展搜索**（直接CALLS + 间接调用Mock）- 当前实现
- **第2层：分段搜索+拼接** - 框架已就绪
- **第3层：LLM推理** - 框架已就绪（待接入LLM）
- **第4层：用户交互** - 框架已就绪

### 3. 间接调用支持
- ✅ 异步调用（work_struct工作队列）
- ✅ 函数指针（ops操作表）
- ✅ 同名函数多ID支持（声明+实现）

## 📊 实现状态

### ✅ v1.0 - MVP版本
- [x] JSON格式知识图谱接口（无需Neo4j）
- [x] 完整的Agent架构（LogParser, EntityLocator, CallChainTracer）
- [x] 主协调器（MasterCoordinator）
- [x] 支持16节点调用链 + 4个间接调用断点
- [x] Mock间接调用数据（临时方案）
- [x] 端到端示例：MMC案例
- [x] **MMC子图优化**：针对性构建子图，性能提升 120x（2分钟 → <1秒）

### 🔬 v1.5 - LLM源码分析（已集成，待启用）
- [x] LLM源码分析模块（SourceCodeBridgeFinder）
- [x] 源码读取工具（SourceCodeReader）
- [x] 异步调用模式识别（work_struct, delayed_work）
- [x] 函数指针模式识别（ops table, callbacks）
- [x] 分层回退机制（LLM优先，Mock兜底）
- [x] 独立测试脚本（test_integrated_source_analysis.py）
- [x] **子图环境就绪**：可在高性能子图上测试LLM功能
- [ ] 集成到主流程（待完善）

**说明**：LLM源码分析功能已完全集成并通过测试，能够自动分析C源码发现异步调用和函数指针连接。目前作为独立模块提供，可通过测试脚本验证效果。后续将集成到主流程替代Mock数据。

### 🚧 v2.0 - 完整LLM增强版（规划中）
- [ ] LLM集成到主流程（替代Mock数据）
- [ ] 基于图谱PRINT关系的日志映射
- [ ] Top-K路径返回
- [ ] LLM指导的搜索剪枝
- [ ] 根因分析和修复建议

## 📁 项目结构

```
kg_based_bug_localization_agent/
├── agents/                          # Agent层
│   ├── base_agent.py                    # Agent基类
│   ├── log_parser_agent.py              # 日志解析
│   ├── entity_locator_agent.py          # 实体定位
│   ├── chain_tracer_agent.py            # 调用链追踪（4层降级）
│   ├── source_code_bridge_finder.py     # LLM源码分析桥接查找器
│   └── llm_analyzer.py                  # LLM分析器（日志定位）
├── coordinator/                     # 协调层
│   └── master_coordinator.py            # 主协调器
├── data/                            # 数据层
│   ├── kg_interface.py                  # 知识图谱接口
│   └── mock_indirect_calls.py           # Mock间接调用（临时）
├── llm/                             # LLM层
│   └── openai_client.py                 # OpenAI客户端封装
├── utils/                           # 工具函数
│   ├── logger.py                        # 日志工具
│   └── source_code_reader.py            # 源码读取工具
├── examples/                        # 示例脚本
│   └── run_mmc_case.py                  # MMC案例（3行日志→16节点）
├── tests/                           # 测试脚本
│   └── verify_16node_path.py            # 验证16节点路径
├── test_integrated_source_analysis.py   # LLM源码分析集成测试
├── test_integration_logic.py            # 集成逻辑测试（Mock）
├── llm_assisted_localization.py         # LLM辅助定位（两阶段）
├── INTEGRATION_SUMMARY.md               # LLM集成总结文档
└── output/                          # 输出结果（自动生成）
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository_url>
cd kg_based_bug_localization_agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 准备数据

知识图谱数据支持两种格式：

**方式1：使用MMC子图（推荐，性能提升120x）**
```
/data/xuao/code_kg_search/linux_test/data/mmc/
├── entity.json       # 实体数据（针对MMC案例的子图）
└── relation.json     # 关系数据
```

**方式2：使用完整图谱**
```
/data/xuao/code_kg_search/linux_test/data/
├── temp_en.json      # 实体数据（完整Linux内核）
└── relations.json    # 关系数据
```

或设置环境变量：
```bash
export KG_DATA_DIR=/path/to/your/data
```

**性能对比**：
- 完整图谱：~120秒加载 + 查询
- MMC子图：<1秒加载 + 查询 ⚡

### 3. 运行示例

```bash
# 使用MMC子图运行（推荐，快速）
cd examples
# 修改 run_mmc_case.py 第50行：
# data_dir = "/data/xuao/code_kg_search/linux_test/data/mmc"
python run_mmc_case.py
```

或使用完整图谱（较慢）：
```bash
# data_dir = "/data/xuao/code_kg_search/linux_test/data"
python examples/run_mmc_case.py
```

**输入**（3行简单日志）：
```
ALL phases bad!
mmc0: tuning execution failed: -1
mmc0: error -1 whilst initialising MMC card
```

**输出**（16节点完整调用链 + 4个间接调用）：
```
✓ 扩展搜索成功，路径长度: 16

调用路径:
  0. dw_mci_pltfm_probe
  1. dw_mci_pltfm_register
  2. dw_mci_probe
  3. dw_mci_init_slot
  4. mmc_add_host (桥接 - 函数指针)
  5. mmc_start_host
  6. _mmc_detect_change
  7. mmc_schedule_delayed_work
  8. mmc_rescan (桥接 - 异步调用)
  9. mmc_rescan_try_freq
  10. mmc_attach_sd
  11. mmc_sd_init_card
  12. mmc_sd_init_uhs_card
  13. mmc_execute_tuning
  14. dw_mci_execute_tuning (桥接 - 函数指针)
  15. dw_mci_hi3660_execute_tuning (桥接 - 函数指针)

统计信息:
  节点数: 16
  间接调用数: 4
```

### 4. 验证测试

```bash
# 运行16节点路径验证脚本
python tests/verify_16node_path.py
```

这个脚本会：
- 检查16个预期节点是否都存在于图谱
- 检查15个相邻节点对的连通性
- 验证BFS能否找到完整路径
- 统计间接调用数

## 📖 使用方法

### 方式1: 使用协调器（推荐）

```python
from coordinator.master_coordinator import MasterCoordinator

# 创建协调器
coordinator = MasterCoordinator(
    data_dir="/data/xuao/code_kg_search/linux_test/data"
)

# 方式1：自动推断起点和终点
error_log = """
ALL phases bad!
mmc0: tuning execution failed: -1
mmc0: error -1 whilst initialising MMC card
"""

result = coordinator.process(error_log)

# 方式2：指定起点和终点
result = coordinator.process_with_specific_functions(
    error_log,
    start_func='dw_mci_pltfm_probe',
    end_func='dw_mci_execute_tuning'
)

# 查看结果
print(f"成功: {result['success']}")
print(f"路径长度: {len(result['chain']['path'])}")
print(f"间接调用数: {len(result['chain']['breaks'])}")

coordinator.close()
```

### 方式2: 单独使用Agent

```python
from data.kg_interface import KnowledgeGraphInterface
from agents.log_parser_agent import LogParserAgent
from agents.entity_locator_agent import EntityLocatorAgent
from agents.chain_tracer_agent import CallChainTracerAgent

# 初始化
kg = KnowledgeGraphInterface(data_dir="/path/to/data")
log_parser = LogParserAgent()
entity_locator = EntityLocatorAgent(kg)
chain_tracer = CallChainTracerAgent(kg)

# 执行流程
parsed_log = log_parser.parse_mmc_log(error_log)
entities = entity_locator.execute(parsed_log)
chain = chain_tracer.execute(
    entities['start_entity'],
    entities['end_entity'],
    max_depth=20
)

kg.close()
```

## 🔧 核心API

### KnowledgeGraphInterface

```python
# 查找函数
func = kg.find_function('dw_mci_probe')

# 获取调用关系
callees = kg.get_callees('dw_mci_probe')  # 支持多ID同名函数
callers = kg.get_callers('mmc_add_host')

# 查找路径（支持间接调用）
path = kg.find_call_path_with_indirect(
    start='dw_mci_pltfm_probe',
    end='dw_mci_hi3660_execute_tuning',
    max_depth=20
)

# 获取函数上下文
context = kg.get_function_context('dw_mci_probe')
# 返回: info, code, callers, callees, variables, related_structs
```

### CallChainTracerAgent

```python
# 执行4层降级搜索
chain = tracer.execute(
    start_entity={'name': 'dw_mci_pltfm_probe', ...},
    end_entity={'name': 'dw_mci_hi3660_execute_tuning', ...},
    max_depth=20
)

# 返回格式
{
    'path': ['func1', 'func2', ...],       # 16个节点
    'edges': [                              # 边类型
        'direct',                           # 直接调用
        {'type': 'indirect', 'bridge': ...} # 间接调用
    ],
    'breaks': [                             # 断点信息
        {
            'position': 4,
            'from': 'dw_mci_init_slot',
            'to': 'mmc_add_host',
            'fixed': True,
            'method': 'mock_indirect_call',
            'bridge': {'bridge_type': 'function_pointer', ...}
        }
    ],
    'method': 'extended_search',            # 使用的层级
    'success': True
}
```

## 📊 数据格式

### 实体文件（temp_en.json）
```json
{
  "FUNCTION": [
    {
      "id": "1548090",
      "name": "dw_mci_pltfm_probe",
      "type": "FUNCTION",
      "source_file": "drivers/mmc/host/dw_mmc-pltfm.c",
      "code": "..."
    }
  ],
  "STRUCT": [...]
}
```

### 关系文件（relations.json）
```json
{
  "CALLS": [
    {
      "head": "1548090",      // caller ID
      "tail": "1548105",      // callee ID
      "type": "CALLS"
    }
  ],
  "DECL_IMPL": [             // 函数声明-实现映射
    {
      "head": "1548105",     // 声明ID
      "tail": "1548089",     // 实现ID
      "type": "DECL_IMPL"
    }
  ]
}
```

### Mock间接调用（临时）
```python
# data/mock_indirect_calls.py
MOCK_ASYNC_CALLS = {
    ("mmc_schedule_delayed_work", "mmc_rescan"): {
        "bridge_type": "async",
        "bridge_entity": "work_struct.func",
        ...
    }
}

MOCK_FUNCTION_POINTER_CALLS = {
    ("mmc_execute_tuning", "dw_mci_execute_tuning"): {
        "bridge_type": "function_pointer",
        "bridge_entity": "mmc_host_ops.execute_tuning",
        ...
    }
}
```

**注意**：Mock数据是临时方案，等图谱完善ASSIGNED_TO关系后将被移除。

## 🧪 测试

### 主流程测试

```bash
# 验证16节点路径
python tests/verify_16node_path.py

# 运行主程序（不使用LLM）
python examples/run_mmc_case.py
```

### LLM源码分析测试

```bash
# 测试LLM源码分析功能（需要LLM API）
python test_integrated_source_analysis.py
```

**测试说明**：
- 测试案例：`mmc_schedule_delayed_work` → `mmc_rescan`
- LLM会分析源码发现通过 `host->detect` 异步连接
- 需要先在脚本中配置API key（第36行）
- 期望输出：
  ```
  ✅ LLM源码分析成功!
     类型: async_work
     桥接: host->detect
     置信度: 1.00
  ```

**集成逻辑测试**（Mock环境）：
```bash
python test_integration_logic.py
```

这个测试验证分层回退机制：
- Layer 1: LLM源码分析
- Layer 2: Mock数据回退
- 向后兼容性测试

## ⚙️ 配置

### 环境变量
- `KG_DATA_DIR`: 数据目录（默认：`/data/xuao/code_kg_search/linux_test/data`）
- `OPENAI_API_KEY`: OpenAI API密钥（可选，用于LLM功能）

### 可调参数
- `max_depth`: 最大搜索深度（默认20）
- `max_same_name_funcs`: 同名函数ID数量警告阈值

## 🎯 MMC子图说明

### 为什么需要子图？

完整的Linux内核知识图谱包含：
- 54万+ 函数
- 100万+ 关系
- 加载时间：~120秒

对于特定案例（如MMC），只需要很小一部分节点和关系。

### MMC子图特点

**数据位置**：`/data/xuao/code_kg_search/linux_test/data/mmc/`

**性能提升**：
- 完整图谱：2分钟
- MMC子图：<1秒
- **提升：120x** ⚡

**功能验证**：
- ✅ 支持16节点调用链
- ✅ 支持4个间接调用（Mock）
- ✅ 所有测试通过
- ✅ **为LLM实验提供高性能环境**

**适用场景**：
- 开发和调试LLM功能
- 快速迭代测试
- MMC案例演示

## 🔮 下一步计划

### Phase 1: LLM源码分析启用（进行中）
1. ✅ **LLM源码分析模块**：已实现并通过测试
2. ✅ **分层回退机制**：LLM优先，Mock兜底
3. ✅ **MMC子图环境**：高性能测试环境已就绪
4. 🔨 **主流程集成**：将LLM源码分析集成到 `run_mmc_case.py`
   - 当前状态：独立模块已就绪，可通过测试脚本验证
   - 下一步：架构调整，让第1层就能使用LLM（而非等到第2层）
   - **优势**：可在MMC子图上快速测试迭代

### Phase 2: 基础增强（待实现）
5. **图谱PRINT关系映射**：使用图谱的日志信息替代Mock规则
6. **Top-K路径返回**：返回多条候选路径供选择
7. **LLM指导剪枝**：利用LLM知识优化搜索方向

### Phase 3: 高级功能（规划中）
8. 根因分析Agent
9. 修复建议Agent
10. Web可视化界面

## 🎯 技术亮点

1. **无需数据库**：纯JSON存储，轻量级部署
2. **多ID同名函数**：正确处理C语言的函数声明和实现
3. **间接调用支持**：识别异步和函数指针调用
4. **分层降级**：从简单到复杂，确保鲁棒性
5. **端到端**：3行日志 → 16节点完整调用链

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

当前优先级：
1. 确认图谱PRINT关系格式
2. 实现Top-K路径返回
3. 设计LLM Prompt模板

## 📄 许可

MIT License

## 📞 联系方式

如有问题或建议，请通过Issue联系。
