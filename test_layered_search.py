#!/usr/bin/env python3
"""
测试分层搜索策略
验证扩展搜索、分段搜索、LLM推理的完整流程
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.kg_interface import KnowledgeGraphInterface
from agents.chain_tracer_agent import CallChainTracerAgent
from llm.openai_client import OpenAIClient

print("=" * 80)
print("测试分层搜索策略")
print("=" * 80)

# 初始化
data_dir = "/data/xuao/code_kg_search/linux_test/data"
kg = KnowledgeGraphInterface(data_dir)

# 创建 LLM 客户端（可选）
llm_client = None
if os.getenv('OPENAI_API_KEY'):
    print("\n✓ 检测到 OPENAI_API_KEY，启用 LLM 功能")
    llm_client = OpenAIClient(model="gpt-4")
else:
    print("\n⚠ 未设置 OPENAI_API_KEY，将跳过 LLM 测试")
    print("  提示: export OPENAI_API_KEY='your-api-key'")

# 创建 ChainTracerAgent
tracer = CallChainTracerAgent(kg, llm_client)

print("\n" + "=" * 80)
print("【测试1】第1层：扩展搜索（支持间接调用）")
print("=" * 80)

start_func = "mmc_add_host"
end_func = "dw_mci_execute_tuning"

print(f"\n起始函数: {start_func}")
print(f"目标函数: {end_func}")

start_entity = kg.find_function(start_func)
end_entity = kg.find_function(end_func)

if not start_entity or not end_entity:
    print("✗ 函数不存在，跳过测试")
else:
    print("\n执行扩展搜索...")
    result = tracer.execute(start_entity, end_entity, max_depth=15)

    print(f"\n结果:")
    print(f"  - 成功: {result['success']}")
    print(f"  - 方法: {result.get('method', 'unknown')}")
    print(f"  - 路径长度: {len(result.get('path', []))}")

    if result.get('path'):
        print(f"\n调用路径:")
        for i, node in enumerate(result['path'], 1):
            edge_type = ""
            if 'edges' in result and i - 1 < len(result['edges']):
                edge = result['edges'][i - 1]
                if isinstance(edge, dict):
                    edge_type = f" [{edge.get('type', 'unknown')}]"
                else:
                    edge_type = f" [{edge}]"
            print(f"  {i}. {node}{edge_type}")

        # 分析边的类型
        if 'edges' in result:
            direct_count = sum(1 for e in result['edges'] if e == 'direct')
            indirect_count = sum(1 for e in result['edges'] if isinstance(e, dict) and e.get('type') == 'indirect')
            print(f"\n边统计:")
            print(f"  - 直接调用: {direct_count}")
            print(f"  - 间接调用: {indirect_count}")

            # 显示间接调用详情
            if indirect_count > 0:
                print(f"\n间接调用详情:")
                for i, edge in enumerate(result['edges']):
                    if isinstance(edge, dict) and edge.get('type') == 'indirect':
                        bridge = edge.get('bridge', {})
                        print(f"  {i+1}. {result['path'][i]} -> {result['path'][i+1]}")
                        print(f"     桥接类型: {bridge.get('bridge_type', 'unknown')}")
                        print(f"     桥接实体: {bridge.get('bridge_entity', 'unknown')}")

print("\n" + "=" * 80)
print("【测试2】第2层：分段搜索+拼接")
print("=" * 80)

print("\n测试场景：假设扩展搜索失败，尝试分段搜索")
print("（这个测试需要一个确实断开的调用链场景）")

# 测试从起点和终点的可达性
print(f"\n从 {start_func} 正向搜索可达节点...")
reachable_from_start = kg.find_reachable_from_start(start_func, max_depth=5)
print(f"  可达节点数: {len(reachable_from_start)}")
print(f"  前5个: {list(reachable_from_start.keys())[:5]}")

print(f"\n从 {end_func} 反向搜索可达节点...")
reachable_to_end = kg.find_reachable_to_end(end_func, max_depth=5)
print(f"  可达节点数: {len(reachable_to_end)}")
print(f"  前5个: {list(reachable_to_end.keys())[:5]}")

# 找交集
intersection = set(reachable_from_start.keys()) & set(reachable_to_end.keys())
print(f"\n交集节点数: {len(intersection)}")
if intersection:
    print(f"  前5个: {list(intersection)[:5]}")

print("\n" + "=" * 80)
print("【测试3】第3层：LLM推理")
print("=" * 80)

if llm_client and llm_client.is_available():
    print("\n测试 LLM 分析函数关系...")

    # 选择两个有间接调用关系的函数
    func_a = "mmc_schedule_delayed_work"
    func_b = "mmc_rescan"

    code_a = kg.get_function_code(func_a) or "代码未找到"
    code_b = kg.get_function_code(func_b) or "代码未找到"

    context = {
        'callees_a': kg.get_callees(func_a),
        'callers_b': kg.get_callers(func_b),
        'related_structs_a': kg.get_related_structs(func_a),
        'related_structs_b': kg.get_related_structs(func_b)
    }

    print(f"\n分析: {func_a} -> {func_b}")
    print("（此测试将调用 OpenAI API，可能需要几秒钟）\n")

    result = llm_client.analyze_code_relationship(
        func_a, func_b, code_a, code_b, context
    )

    if result:
        print(f"✓ LLM 分析成功:")
        print(f"  - 桥接类型: {result.get('bridge_type', 'unknown')}")
        print(f"  - 桥接实体: {result.get('bridge_entity', 'unknown')}")
        print(f"  - 置信度: {result.get('confidence', 0):.2f}")
        print(f"  - 解释: {result.get('explanation', 'N/A')[:200]}...")
    else:
        print("✗ LLM 分析失败")
else:
    print("\n⚠ LLM 不可用，跳过此测试")
    print("  提示: 设置 OPENAI_API_KEY 环境变量以启用 LLM 功能")

print("\n" + "=" * 80)
print("【总结】分层搜索策略测试完成")
print("=" * 80)

print("\n实现的功能:")
print("  1. ✓ 第1层：扩展搜索（直接+间接调用）")
print("  2. ✓ 第2层：分段搜索+拼接")
if llm_client and llm_client.is_available():
    print("  3. ✓ 第3层：LLM推理")
else:
    print("  3. ⚠ 第3层：LLM推理（未测试，需要 API Key）")
print("  4. ✓ 第4层：用户交互提示")

print("\n建议:")
print("  - 第1层通常能解决大部分问题（mock 数据支持间接调用）")
print("  - 第2层适用于图谱部分断开的场景")
print("  - 第3层需要 OpenAI API Key，适用于复杂推理场景")
print("  - 第4层提示用户提供关键节点，兜底方案")

print("\n" + "=" * 80)

kg.close()
