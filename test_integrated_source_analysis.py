#!/usr/bin/env python3
"""
测试集成后的LLM源码分析功能
验证ChainTracerAgent是否能使用LLM分析源码来桥接断裂的调用链
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.kg_interface import KnowledgeGraphInterface
from agents.chain_tracer_agent import CallChainTracerAgent
from agents.llm_analyzer import LLMAnalyzer


def test_broken_chain_with_llm():
    """测试断裂调用链的LLM源码分析修复"""

    print("="*80)
    print("测试：LLM源码分析集成")
    print("="*80)

    # 1. 初始化知识图谱
    print("\n[1/4] 初始化知识图谱...")
    kg = KnowledgeGraphInterface(
        data_dir="/data/xuao/code_kg_search/linux_test/data"
    )
    print(f"  ✓ 知识图谱加载完成")

    # 2. 初始化LLM客户端
    print("\n[2/4] 初始化LLM客户端...")
    llm = LLMAnalyzer(
        api_key="",
        base_url="http://10.12.208.86:8502"
    )
    print(f"  ✓ LLM客户端初始化完成 (model: {llm.model})")

    # 3. 初始化CallChainTracerAgent（带LLM）
    print("\n[3/4] 初始化CallChainTracerAgent...")
    agent = CallChainTracerAgent(kg=kg, llm_client=llm)
    print(f"  ✓ Agent初始化完成")
    print(f"  - bridge_finder: {agent.bridge_finder is not None}")
    print(f"  - source_reader: {agent.source_reader is not None}")

    # 4. 测试断裂的调用链
    print("\n[4/4] 测试断裂调用链修复...")
    print("\n测试案例: mmc_schedule_delayed_work → mmc_rescan")
    print("  这个连接通过 host->detect 在 mmc_alloc_host 中初始化")
    print("  期望: LLM源码分析能够发现这个连接\n")

    # 查询这两个函数
    func_a = "mmc_schedule_delayed_work"
    func_b = "mmc_rescan"

    func_a_ids = kg.get_function_ids(func_a)
    func_b_ids = kg.get_function_ids(func_b)

    print(f"  {func_a}: {len(func_a_ids)} 个实例")
    print(f"  {func_b}: {len(func_b_ids)} 个实例")

    if not func_a_ids or not func_b_ids:
        print("\n❌ 测试失败: 无法找到测试函数")
        return

    # 直接测试_check_async_pattern方法
    print("\n开始LLM源码分析...")
    print("-" * 80)

    result = agent._check_async_pattern(func_a, func_b)

    print("-" * 80)

    if result:
        print("\n✅ 桥接成功!")
        print(f"  桥接类型: {result.get('bridge_type', 'N/A')}")
        print(f"  桥接实体: {result.get('bridge_entity', 'N/A')}")
        print(f"  方法: {result.get('method', 'N/A')}")
        print(f"  置信度: {result.get('confidence', 0.0):.2f}")
        if result.get('explanation'):
            print(f"\n  解释: {result['explanation'][:200]}...")
    else:
        print("\n❌ 未找到桥接")

    # 显示统计信息
    print("\n" + "="*80)
    print("统计信息")
    print("="*80)
    for key, value in agent.stats.items():
        print(f"  {key}: {value}")

    # 验证是否使用了LLM源码分析
    if agent.stats.get('fixed_by_source_analysis', 0) > 0:
        print("\n✅ LLM源码分析功能正常工作!")
    else:
        print("\n⚠️  LLM源码分析未被使用，可能回退到了Mock数据")

    return result


def main():
    try:
        result = test_broken_chain_with_llm()

        print("\n" + "="*80)
        print("测试完成")
        print("="*80)

        if result and result.get('method') == 'llm_source_analysis':
            print("\n✅ 集成测试通过! LLM源码分析成功替代了Mock数据。")
        elif result:
            print("\n⚠️  找到了桥接，但使用的是Mock数据而非LLM分析。")
        else:
            print("\n❌ 未找到桥接。")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
