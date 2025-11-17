# Bug定位系统 - 基于知识图谱与LLM

一个基于知识图谱的Linux内核Bug定位系统，结合大语言模型(LLM)辅助间接调用检测，实现从错误日志到可疑代码路径的自动化追踪。

## 📋 目录

- [核心功能](#核心功能)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [主要特性](#主要特性)
- [配置说明](#配置说明)
- [使用示例](#使用示例)
- [依赖项](#依赖项)
- [未来计划](#未来计划)

---

## 🎯 核心功能

### 1. Top-K路径搜索
- **多路径分析**：返回Top-K条从入口到错误点的调用链
- **得分排序**：基于路径长度、间接调用数量、关键函数覆盖率综合评分
- **关键函数检测**：自动识别日志中的关键函数并优先选择经过这些函数的路径

### 2. LLM辅助间接调用检测
- **函数指针调用检测**：LLM分析源码提取结构体字段，查询图谱ASSIGNED_TO关系
- **异步调用检测**：识别`schedule_*`、`queue_work`等异步调度函数，追踪工作队列回调
- **预处理模式**：BFS前批量处理配置的函数，缓存结果供搜索使用

### 3. 双模式支持
- **自动推断模式**：从日志自动提取入口、错误点和关键函数
- **手动指定模式**：显式指定起点、终点和中间节点

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      MasterCoordinator                       │
│                      (主协调器)                               │
└───────────────┬─────────────────────────────────────────────┘
                │
        ┌───────┼───────┬───────────┬─────────────┐
        │       │       │           │             │
        ▼       ▼       ▼           ▼             ▼
   ┌────────┬────────┬──────┬──────────┬─────────────────┐
   │  Log   │Entity  │Chain │ Source   │   LLM Indirect  │
   │ Parser │Locator │Tracer│Code Bridge│  Call Detector │
   └────────┴────────┴──────┴──────────┴─────────────────┘
                │
                ▼
        ┌───────────────┐
        │ KG Interface  │
        │ (知识图谱)     │
        └───────────────┘
```

### Agent系统

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **LogParser** | 解析错误日志 | 日志文本 | 错误码、关键函数、推断入口/错误点 |
| **EntityLocator** | 在图谱中定位函数实体 | 函数名列表 | 函数实体(id, name, file) |
| **ChainTracer** | Top-K路径搜索 | 起点、终点、中间节点 | Top-K路径及得分 |
| **SourceCodeBridgeFinder** | LLM源码断点连接 | 断开的路径段 | 源码级连接建议 |

### 数据层

- **KnowledgeGraphInterface**：图谱查询接口
  - 函数查询（精确/模糊）
  - CALLS关系查询
  - ASSIGNED_TO关系查询（字段→函数映射）
  - Top-K路径搜索（BFS + 优先队列）

- **LLMIndirectCallDetector**：LLM间接调用检测
  - 函数指针字段提取
  - 异步调用参数提取
  - 批量预处理与缓存

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API Key

**⚠️ 目前使用OpenAI API，需要配置API Key以启用LLM功能**

**方式1：环境变量（推荐）**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

**方式2：修改代码**

在 `llm/openai_client.py` 第21行直接设置，或在调用时传入：

```python
# examples/run_mmc_case_topk.py
from llm.openai_client import OpenAIClient

coordinator = MasterCoordinator(
    data_dir=data_dir,
    llm_client=OpenAIClient(
        api_key="your-api-key",
        base_url="http://your-api-endpoint:8502"  # 可选，用于自定义endpoint
    ),
    enable_llm_detection=True
)
```

**方式3：不使用LLM（仅使用Mock数据）**
```python
# 不启用LLM，仅使用图谱+Mock数据
coordinator = MasterCoordinator(data_dir=data_dir, enable_llm_detection=False)
```

### 3. 运行示例

```bash
# 标准模式（不使用LLM，仅图谱+Mock）
python examples/run_mmc_case_topk.py

# LLM辅助模式（需要配置API Key）
python examples/run_mmc_case_topk.py --llm
```

---

## ✨ 主要特性

### 1. Top-K路径搜索

**传统方法问题**：单路径可能不准确，需要人工逐个尝试

**我们的方案**：
- 返回Top-K条路径供开发者选择
- 综合得分：`score = -length + bonus_indirect + bonus_key_functions`
- 路径排序：优先展示最可能的路径

**示例输出**：
```
找到 5 条路径:

路径 #1 (长度=16, 间接调用=3, 平均行号=245.3, 得分=150.00, 关键函数覆盖率=67%)
  0. dw_mci_pltfm_probe
  1. mmc_add_host
  ...
  8. mmc_attach_mmc ✓          ← 青色高亮（关键函数）
  9. mmc_init_card
  ...
  14. mmc_execute_tuning ✓
  15. dw_mci_execute_tuning (函数指针)  ← 黄色高亮（间接调用）
  ⚠ 未经过的关键函数: dw_mci_hi3660_execute_tuning

路径 #2 (长度=18, 间接调用=2, 得分=120.00, 关键函数覆盖率=100%)
  ...
```

### 2. 关键函数检测与得分调整

**日志格式**（栈式存储，逆序）：
```
ALL phases bad!                                # 最深函数
mmc0: tuning execution failed: -1              # 中间函数
mmc0: error -1 whilst initialising MMC card    # 较早函数
```

**系统行为**：
- 提取关键函数：`[dw_mci_hi3660_execute_tuning, mmc_execute_tuning, mmc_attach_mmc]`
- 检查每条路径经过的关键函数
- 得分调整：每匹配一个关键函数 **+50分**
- 显示增强：
  - 青色高亮关键函数
  - 显示覆盖率
  - 提示未经过的关键函数

### 3. LLM辅助间接调用检测

#### 问题背景
知识图谱无法静态分析函数指针和异步调用，导致路径断开：
```c
// 函数指针调用：图谱只有 mmc_execute_tuning，缺失具体实现
host->ops->execute_tuning(host, opcode);  // 实际调用 dw_mci_execute_tuning

// 异步调用：图谱只有 schedule 调用，缺失回调函数
mmc_schedule_delayed_work(&host->detect, 0);  // 实际回调 mmc_rescan
```

#### 解决方案
**两阶段检测**：

**阶段1：LLM源码分析**
- 函数指针：提取字段名 `ops.execute_tuning`
- 异步调用：提取参数字段名 `detect`

**阶段2：图谱查询**
- 查询ASSIGNED_TO关系：`detect → mmc_rescan`
- Fallback到Mock数据（如果图谱不完善）

**预处理模式**：
```yaml
# config/indirect_call_detection.yaml
functions_need_llm_detection:
  - mmc_execute_tuning
  - dw_mci_execute_tuning

async_call_detection:
  keywords:
    - schedule
    - delayed_work
    - queue_work
```

### 4. 显示优化

**路径可视化**：
- **普通函数**：白色
- **关键函数**：青色 + ✓标记
- **间接调用**：黄色 + 类型标注（函数指针/异步调用）
- **调用行号**：灰色显示（用于代码定位）

**统计信息**：
- 路径长度
- 间接调用数量
- 平均调用行号
- 得分
- 关键函数覆盖率

---

## ⚙️ 配置说明

### 1. 间接调用检测配置

**文件**：`config/indirect_call_detection.yaml`

```yaml
# 函数指针检测
functions_need_llm_detection:
  - mmc_execute_tuning      # 需要LLM检测的函数

# 异步调用检测
async_call_detection:
  keywords:                  # 识别异步函数的关键字
    - schedule
    - delayed_work
    - queue_work

  known_async_functions:     # 显式列出的异步函数
    - mmc_schedule_delayed_work
```

### 2. Mock数据配置

**文件**：`data/mock_indirect_calls.py`

当图谱不完善时使用Mock数据作为Fallback：

```python
MOCK_INDIRECT_CALLS = {
    "mmc_execute_tuning": {
        "ops.execute_tuning": ["dw_mci_execute_tuning"]
    }
}

MOCK_ASYNC_ASSIGNED_TO = {
    "detect": ["mmc_rescan"]
}
```

---

## 📖 使用示例

### 方式1：自动推断（从日志提取）

```python
from coordinator.master_coordinator import MasterCoordinator

coordinator = MasterCoordinator(
    data_dir="/path/to/kg/data",
    enable_llm_detection=True
)

result = coordinator.process_top_k(
    log_text="""
    ALL phases bad!
    mmc0: tuning execution failed: -1
    mmc0: error -1 whilst initialising MMC card
    """,
    k=5  # 返回Top-5路径
)
```

### 方式2：手动指定（显式控制）

```python
result = coordinator.process_top_k_with_specific_functions(
    log_text="...",
    start_func='dw_mci_pltfm_probe',
    end_func='dw_mci_execute_tuning',
    intermediate_funcs=[
        'mmc_attach_mmc',
        'mmc_execute_tuning',
        'dw_mci_hi3660_execute_tuning'
    ],
    k=5
)
```

### 结果解析

```python
for path in result['paths']:
    print(f"路径长度: {path['length']}")
    print(f"得分: {path['score']}")
    print(f"路径: {' -> '.join(path['path'])}")

    # 关键函数覆盖率
    total_keys = len(path['matched_key_functions']) + len(path['missed_key_functions'])
    coverage = len(path['matched_key_functions']) / total_keys if total_keys > 0 else 0
    print(f"关键函数覆盖率: {coverage:.0%}")

    print(f"间接调用: {path['indirect_count']}")
```

---

## 📦 依赖项

主要依赖（见 `requirements.txt`）：

```
openai>=1.0.0          # LLM API调用
loguru>=0.7.0          # 日志记录
pyyaml>=6.0            # 配置文件解析
rich>=13.0.0           # 终端输出美化
```

**可选依赖**：
- 如果不使用LLM功能，可以不安装`openai`包
- 系统会自动检测并降级到纯图谱+Mock模式

---

## 🔮 未来计划

### 短期计划

#### 1. 完善知识图谱
**目标**：消除Mock数据依赖

**当前状态**：
- 使用Mock数据补充图谱缺失的间接调用关系
- ASSIGNED_TO关系不完整（函数指针和异步调用的字段→函数映射）

**待完成**：
- [ ] 获取完整的Linux内核知识图谱
- [ ] 验证ASSIGNED_TO关系覆盖率
- [ ] 逐步减少Mock数据使用
- [ ] 建立图谱质量评估机制

#### 2. 子图定位模块
**背景**：完整Linux内核图谱规模庞大，全图搜索效率低

**待评估**：
- [ ] 根据获取到的图谱规模，评估是否需要子图定位
- [ ] 性能测试：全图BFS vs 子图BFS
- [ ] 如果需要：基于错误码/子系统/文件路径缩小搜索范围

**实现方式（如果需要）**：
```
LLM分析日志 → 确定子系统/模块 → 提取子图 → 局部Top-K搜索
```

#### 3. 改进入口函数推断
**当前方法**：规则化模式匹配（如`*_probe`、`*_init`）

**问题**：
- 规则过于简单，容易误判
- 不同子系统的入口模式不同
- 缺少上下文分析

**改进方向**：
- [ ] **图谱辅助**：从图谱中查询函数调用深度，选择调用链顶层函数
- [ ] **LLM分析**：结合日志上下文和代码结构，智能推断真实入口
- [ ] **混合策略**：图谱提供候选 + LLM排序选择

示例流程：
```python
# 步骤1: 图谱提供候选（基于调用深度、子系统）
candidates = kg.find_entry_candidates(
    subsystem="mmc",
    error_func="dw_mci_execute_tuning",
    depth_threshold=0  # 只选择顶层函数
)
# → [dw_mci_pltfm_probe, dw_mci_init, mmc_start_host, ...]

# 步骤2: LLM排序（基于日志上下文）
inferred_entry = llm.rank_entry_points(
    candidates=candidates,
    log_context=log_text,
    call_graph_snippet=kg.get_subgraph(candidates)
)
# → dw_mci_pltfm_probe (LLM分析后的最佳入口)
```

### 中期计划

#### 4. 扩展LLM调用场景

**a) 断点连接增强**
- [ ] 当图谱路径中断时，LLM分析源码找连接点
- [ ] 实现细粒度源码分析（已有基础框架`SourceCodeBridgeFinder`，待完善）
- [ ] 缓存LLM分析结果，避免重复调用

**b) 多模态分析**
- [ ] LLM分析配置文件（Kconfig、Makefile）辅助定位
- [ ] 结合Git历史和issue记录
- [ ] Patch分析：识别相关代码变更

**c) 交互式修复建议**
- [ ] LLM建议代码修复方案
- [ ] 生成测试用例
- [ ] 根据调用链生成调试脚本

**d) 提示词优化**
- [ ] Few-shot learning：提供典型案例
- [ ] 上下文增强：传递更多图谱信息
- [ ] 结果验证：LLM自我纠错机制

#### 5. 性能优化

- [ ] 图谱查询缓存
- [ ] 并行路径搜索
- [ ] 增量BFS（复用已搜索的部分路径）
- [ ] 优先队列优化（更智能的剪枝策略）

#### 6. 可视化工具

- [ ] Web界面展示调用链
- [ ] 交互式路径探索
- [ ] 源码高亮显示
- [ ] 路径对比视图

---

## 📚 项目结构

```
kg_based_bug_localization_agent/
├── agents/                          # Agent系统
│   ├── base_agent.py               # Agent基类
│   ├── chain_tracer_agent.py       # 调用链追踪（核心）
│   ├── entity_locator_agent.py     # 实体定位
│   ├── log_parser_agent.py         # 日志解析
│   └── source_code_bridge_finder.py # 源码断点连接
├── coordinator/                     # 协调器
│   └── master_coordinator.py       # 主协调器（入口）
├── data/                           # 数据层
│   ├── kg_interface.py             # 知识图谱接口
│   └── mock_indirect_calls.py      # Mock数据
├── utils/                          # 工具类
│   ├── llm_indirect_call_detector.py # LLM间接调用检测
│   ├── source_code_reader.py       # 源码读取
│   └── logger.py                   # 日志工具
├── llm/                            # LLM客户端
│   └── openai_client.py            # OpenAI API封装
├── config/                         # 配置
│   ├── settings.py                 # 系统配置
│   └── indirect_call_detection.yaml # 间接调用检测配置
├── examples/                       # 使用示例
│   └── run_mmc_case_topk.py        # MMC案例（Top-K版本）
├── output/                         # 输出目录
├── requirements.txt                # 依赖项
└── README.md                       # 本文件
```

---

## 🤝 贡献指南

欢迎贡献！主要方向：

1. **图谱完善**：提供更完整的Linux内核知识图谱
2. **LLM优化**：改进prompt工程，提升检测准确率
3. **性能优化**：大规模图谱搜索加速
4. **新特性**：子图定位、可视化、多模态分析等

---

## 📄 许可证

[待定]

---

## 📧 联系方式

如有问题或建议，请联系项目维护者。

---

**最后更新**：2025-11-17
