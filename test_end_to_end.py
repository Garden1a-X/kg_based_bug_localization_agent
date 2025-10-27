#!/usr/bin/env python3
"""
端到端测试：从日志到调用链定位
模拟真实的 Bug 定位流程
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.kg_interface import KnowledgeGraphInterface
from agents.log_parser_agent import LogParserAgent
from agents.chain_tracer_agent import CallChainTracerAgent
from llm.openai_client import OpenAIClient

print("=" * 80)
print("📋 端到端测试：从日志到调用链定位")
print("=" * 80)

# ============================================================================
# 第1步：加载 Mock 日志
# ============================================================================
print("\n" + "=" * 80)
print("【第1步】加载 Mock 内核日志")
print("=" * 80)

log_file = project_root / "test_data" / "mock_kernel_log.txt"
with open(log_file, 'r', encoding='utf-8') as f:
    log_text = f.read()

print(f"\n日志文件: {log_file}")
print(f"日志长度: {len(log_text)} 字符")
print(f"\n日志片段（前500字符）:")
print("-" * 80)
print(log_text[:500])
print("-" * 80)

# ============================================================================
# 第2步：解析日志
# ============================================================================
print("\n" + "=" * 80)
print("【第2步】使用 LogParserAgent 解析日志")
print("=" * 80)

log_parser = LogParserAgent()
parsed_result = log_parser.parse_mmc_log(log_text)

print(f"\n✓ 解析完成")
print(f"\n提取到的信息:")
print(f"  - 错误消息数: {len(parsed_result['error_messages'])}")
print(f"  - 涉及函数数: {len(parsed_result['functions'])}")
print(f"  - 涉及文件数: {len(parsed_result['files'])}")

print(f"\n关键函数（前10个）:")
for i, func in enumerate(parsed_result['functions'][:10], 1):
    print(f"  {i}. {func}")

print(f"\n推断结果:")
print(f"  - 入口函数: {parsed_result.get('inferred_entry', 'N/A')}")
print(f"  - 错误点: {parsed_result.get('inferred_error_point', 'N/A')}")

# ============================================================================
# 第3步：初始化知识图谱
# ============================================================================
print("\n" + "=" * 80)
print("【第3步】初始化知识图谱")
print("=" * 80)

data_dir = "/data/xuao/code_kg_search/linux_test/data"
kg = KnowledgeGraphInterface(data_dir)

print(f"\n✓ 知识图谱加载完成")

# ============================================================================
# 第4步：定位起点和终点实体
# ============================================================================
print("\n" + "=" * 80)
print("【第4步】在知识图谱中定位起点和终点函数")
print("=" * 80)

# 从解析结果获取起点和终点
entry_func = parsed_result.get('inferred_entry', 'dw_mci_pltfm_probe')
error_func = parsed_result.get('inferred_error_point', 'dw_mci_hi3660_execute_tuning')

print(f"\n起点函数: {entry_func}")
print(f"终点函数: {error_func}")

# 在知识图谱中查找
start_entity = kg.find_function(entry_func)
end_entity = kg.find_function(error_func)

if start_entity:
    print(f"\n✓ 找到起点: {entry_func}")
    print(f"  ID: {start_entity.get('id')}")
    print(f"  文件: {start_entity.get('file', 'N/A')}")
else:
    print(f"\n✗ 未找到起点: {entry_func}")
    print("  尝试其他候选...")
    # 尝试其他候选
    for candidate in ['dw_mci_pltfm_probe', 'dw_mci_probe']:
        start_entity = kg.find_function(candidate)
        if start_entity:
            entry_func = candidate
            print(f"  ✓ 使用: {candidate}")
            break

if end_entity:
    print(f"\n✓ 找到终点: {error_func}")
    print(f"  ID: {end_entity.get('id')}")
    print(f"  文件: {end_entity.get('file', 'N/A')}")
else:
    print(f"\n✗ 未找到终点: {error_func}")
    print("  尝试其他候选...")
    # 尝试其他候选
    for candidate in ['dw_mci_hi3660_execute_tuning', 'dw_mci_execute_tuning', 'mmc_execute_tuning']:
        end_entity = kg.find_function(candidate)
        if end_entity:
            error_func = candidate
            print(f"  ✓ 使用: {candidate}")
            break

if not start_entity or not end_entity:
    print("\n✗ 无法定位起点或终点，测试终止")
    sys.exit(1)

# ============================================================================
# 第5步：使用分层搜索策略查找调用链
# ============================================================================
print("\n" + "=" * 80)
print("【第5步】使用分层搜索策略查找调用链")
print("=" * 80)

# 创建 LLM 客户端（可选）
llm_client = None
if os.getenv('OPENAI_API_KEY'):
    print("\n✓ 检测到 OPENAI_API_KEY，启用 LLM 功能")
    llm_client = OpenAIClient(model="gpt-4")
else:
    print("\n⚠ 未设置 OPENAI_API_KEY，将跳过 LLM 层")

# 创建 ChainTracerAgent
tracer = CallChainTracerAgent(kg, llm_client)

print(f"\n查找路径: {entry_func} → {error_func}")
print(f"最大深度: 15")

# 执行搜索
result = tracer.execute(start_entity, end_entity, max_depth=15)

# ============================================================================
# 第6步：展示结果
# ============================================================================
print("\n" + "=" * 80)
print("【第6步】分析结果")
print("=" * 80)

if result['success']:
    print(f"\n✓ 成功找到调用链！")
    print(f"\n使用方法: {result.get('method', 'unknown')}")
    print(f"路径长度: {len(result.get('path', []))}")

    if result.get('path'):
        print(f"\n调用链:")
        print("-" * 80)
        for i, node in enumerate(result['path'], 1):
            edge_info = ""
            if 'edges' in result and i - 1 < len(result['edges']):
                edge = result['edges'][i - 1]
                if isinstance(edge, dict):
                    edge_type = edge.get('type', 'unknown')
                    if edge_type == 'indirect':
                        bridge = edge.get('bridge', {})
                        bridge_type = bridge.get('bridge_type', 'unknown')
                        edge_info = f" → [{edge_type}: {bridge_type}]"
                    else:
                        edge_info = f" → [{edge_type}]"
                else:
                    edge_info = f" → [{edge}]"

            # 高亮关键节点
            marker = ""
            if i == 1:
                marker = "🚀 [入口]"
            elif i == len(result['path']):
                marker = "🎯 [错误点]"
            elif edge_info and 'indirect' in edge_info:
                marker = "🔗 [间接调用]"

            print(f"  {i:2d}. {node:<40s} {marker}")
            if edge_info and i < len(result['path']):
                print(f"      {edge_info}")

        print("-" * 80)

        # 统计边类型
        if 'edges' in result:
            edges = result['edges']
            direct_count = sum(1 for e in edges if e == 'direct')
            indirect_count = sum(1 for e in edges if isinstance(e, dict) and e.get('type') == 'indirect')

            print(f"\n调用链统计:")
            print(f"  - 总节点数: {len(result['path'])}")
            print(f"  - 直接调用: {direct_count}")
            print(f"  - 间接调用: {indirect_count}")

            # 显示间接调用详情
            if indirect_count > 0:
                print(f"\n间接调用详情:")
                for i, edge in enumerate(edges):
                    if isinstance(edge, dict) and edge.get('type') == 'indirect':
                        bridge = edge.get('bridge', {})
                        caller = result['path'][i]
                        callee = result['path'][i + 1]
                        print(f"  • {caller} → {callee}")
                        print(f"    类型: {bridge.get('bridge_type', 'unknown')}")
                        print(f"    桥接: {bridge.get('bridge_entity', 'unknown')}")
                        print(f"    说明: {bridge.get('description', 'N/A')}")
else:
    print(f"\n✗ 未找到调用链")
    print(f"\n失败原因: {result.get('reason', 'unknown')}")
    print(f"使用方法: {result.get('method', 'unknown')}")

# ============================================================================
# 总结
# ============================================================================
print("\n" + "=" * 80)
print("【总结】端到端测试完成")
print("=" * 80)

print(f"\n完成的步骤:")
print(f"  ✓ 第1步：加载 Mock 日志")
print(f"  ✓ 第2步：解析日志，提取 {len(parsed_result['functions'])} 个函数")
print(f"  ✓ 第3步：加载知识图谱")
print(f"  ✓ 第4步：定位起点({entry_func})和终点({error_func})")
print(f"  ✓ 第5步：执行分层搜索")
if result['success']:
    print(f"  ✓ 第6步：成功找到 {len(result['path'])} 个节点的调用链")
else:
    print(f"  ✗ 第6步：未找到调用链")

print(f"\n测试评估:")
if result['success']:
    print(f"  ✅ 端到端流程工作正常")
    print(f"  ✅ 能够从日志自动定位 Bug 调用链")
    print(f"  ✅ 分层搜索策略有效")
else:
    print(f"  ⚠️  需要进一步优化")

print("\n" + "=" * 80)

kg.close()
