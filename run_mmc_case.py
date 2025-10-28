#!/usr/bin/env python3
"""
MMC案例：完整调用链追踪演示
使用带LLM源码分析的CallChainTracerAgent追踪从驱动初始化到执行tuning的完整调用链
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.kg_interface import KnowledgeGraphInterface
from agents.chain_tracer_agent import CallChainTracerAgent
from agents.llm_analyzer import LLMAnalyzer


def print_section(title):
    """打印分节标题"""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")


def print_path_with_breaks(result):
    """打印路径和断裂信息"""
    path = result.get('path', [])
    breaks = result.get('breaks', [])
    edges = result.get('edges', [])

    print(f"路径长度: {len(path)} 个函数")
    print(f"断裂数量: {len(breaks)} 个\n")

    # 打印路径
    print("调用链路径:")
    for i, func in enumerate(path):
        # 检查这个位置是否有断裂
        break_info = None
        for b in breaks:
            if b['position'] == i:
                break_info = b
                break

        # 打印函数
        if break_info:
            # 这是断裂的起点
            print(f"  [{i}] {func}")
            if break_info['fixed']:
                method = break_info.get('method', 'unknown')
                bridge_entity = break_info.get('bridge', {}).get('bridge_entity', 'N/A')

                # 判断修复方法
                if method == 'llm_source_analysis':
                    print(f"      ↓ [断裂-LLM修复] 桥接: {bridge_entity}")
                elif method == 'mock_indirect_call':
                    print(f"      ↓ [断裂-Mock修复] 桥接: {bridge_entity}")
                else:
                    print(f"      ↓ [断裂-{method}] 桥接: {bridge_entity}")
            else:
                print(f"      ↓ [断裂-未修复]")
        else:
            # 正常的直接调用
            if i < len(edges):
                edge = edges[i]
                if isinstance(edge, dict) and edge.get('type') == 'indirect':
                    print(f"  [{i}] {func}")
                    print(f"      ↓ [间接调用]")
                else:
                    print(f"  [{i}] {func}")
                    if i < len(path) - 1:
                        print(f"      ↓")
            else:
                print(f"  [{i}] {func}")


def print_statistics(stats):
    """打印统计信息"""
    print_section("统计信息")

    print("断裂修复统计:")
    print(f"  总断裂数: {stats.get('total_breaks', 0)}")
    print(f"  规则修复: {stats.get('fixed_by_rules', 0)}")
    print(f"  LLM源码分析修复: {stats.get('fixed_by_source_analysis', 0)} ✨")
    print(f"  LLM推理修复: {stats.get('fixed_by_llm', 0)}")
    print(f"  未修复: {stats.get('unfixed', 0)}")

    total_fixed = (stats.get('fixed_by_rules', 0) +
                   stats.get('fixed_by_source_analysis', 0) +
                   stats.get('fixed_by_llm', 0))
    total = stats.get('total_breaks', 0)

    if total > 0:
        success_rate = (total_fixed / total) * 100
        llm_contribution = (stats.get('fixed_by_source_analysis', 0) / total) * 100
        print(f"\n  修复成功率: {success_rate:.1f}%")
        print(f"  LLM贡献率: {llm_contribution:.1f}%")


def run_case_with_llm(kg_data_dir, llm_api_url):
    """运行带LLM的案例"""
    print_section("初始化（带LLM源码分析）")

    # 1. 初始化知识图谱
    print("[1/3] 加载知识图谱...")
    kg = KnowledgeGraphInterface(data_dir=kg_data_dir)
    print("  ✓ 知识图谱加载完成\n")

    # 2. 初始化LLM客户端
    print("[2/3] 初始化LLM客户端...")
    llm = LLMAnalyzer(api_key="", base_url=llm_api_url)
    print(f"  ✓ LLM客户端初始化完成 (model: {llm.model})\n")

    # 3. 创建Agent
    print("[3/3] 创建CallChainTracerAgent...")
    agent = CallChainTracerAgent(kg=kg, llm_client=llm)
    print("  ✓ Agent创建完成")
    print(f"  - LLM源码分析: {'启用' if agent.bridge_finder else '禁用'}")

    return agent, kg


def run_case_without_llm(kg_data_dir):
    """运行不带LLM的案例（对照组）"""
    print_section("初始化（纯Mock模式）")

    # 1. 初始化知识图谱
    print("[1/2] 加载知识图谱...")
    kg = KnowledgeGraphInterface(data_dir=kg_data_dir)
    print("  ✓ 知识图谱加载完成\n")

    # 2. 创建Agent（不传LLM）
    print("[2/2] 创建CallChainTracerAgent...")
    agent = CallChainTracerAgent(kg=kg, llm_client=None)
    print("  ✓ Agent创建完成")
    print(f"  - LLM源码分析: {'启用' if agent.bridge_finder else '禁用'}")

    return agent, kg


def trace_mmc_case(agent, kg, start_func, end_func):
    """追踪MMC案例的调用链"""
    print_section(f"追踪调用链: {start_func} → {end_func}")

    # 获取起点和终点实体
    start_ids = kg.get_function_ids(start_func)
    end_ids = kg.get_function_ids(end_func)

    if not start_ids:
        print(f"❌ 起点函数不存在: {start_func}")
        return None

    if not end_ids:
        print(f"❌ 终点函数不存在: {end_func}")
        return None

    print(f"起点: {start_func} ({len(start_ids)} 个实例)")
    print(f"终点: {end_func} ({len(end_ids)} 个实例)\n")

    start_entity = kg.get_function_info(start_ids[0])
    end_entity = kg.get_function_info(end_ids[0])

    # 追踪调用链
    result = agent.trace_chain(start_entity, end_entity, max_depth=10)

    if result['success']:
        print(f"\n✅ 调用链追踪成功 (方法: {result['method']})")
        return result
    else:
        print(f"\n❌ 调用链追踪失败")
        if result.get('user_interaction_needed'):
            print(f"   {result.get('message')}")
        return result


def main():
    """主函数"""
    print("="*80)
    print("MMC案例：完整调用链追踪演示")
    print("对比 LLM源码分析 vs 纯Mock模式")
    print("="*80)

    # 配置
    kg_data_dir = "/data/xuao/code_kg_search/linux_test/data"
    llm_api_url = "http://10.12.208.86:8502"

    # 测试案例
    test_cases = [
        ("dw_mci_probe", "dw_mci_init_slot"),
        ("dw_mci_init_slot", "mmc_add_host"),
        ("mmc_add_host", "mmc_rescan"),
        ("mmc_rescan", "mmc_execute_tuning"),
    ]

    # 选择一个有代表性的案例
    start_func, end_func = "dw_mci_probe", "mmc_rescan"

    print(f"\n测试案例: {start_func} → {end_func}")
    print(f"这个案例包含 mmc_schedule_delayed_work → mmc_rescan 的异步断裂")

    # ===== 实验1: 带LLM =====
    print("\n" + "🔬 "*40)
    print("实验1: 使用LLM源码分析")
    print("🔬 "*40)

    agent_with_llm, kg = run_case_with_llm(kg_data_dir, llm_api_url)
    result_with_llm = trace_mmc_case(agent_with_llm, kg, start_func, end_func)

    if result_with_llm and result_with_llm['success']:
        print_path_with_breaks(result_with_llm)
        print_statistics(result_with_llm['stats'])

    # ===== 实验2: 不带LLM =====
    print("\n" + "🔬 "*40)
    print("实验2: 纯Mock模式（对照组）")
    print("🔬 "*40)

    agent_without_llm, kg = run_case_without_llm(kg_data_dir)
    result_without_llm = trace_mmc_case(agent_without_llm, kg, start_func, end_func)

    if result_without_llm and result_without_llm['success']:
        print_path_with_breaks(result_without_llm)
        print_statistics(result_without_llm['stats'])

    # ===== 对比分析 =====
    print_section("对比分析")

    if result_with_llm and result_without_llm:
        stats_llm = result_with_llm['stats']
        stats_mock = result_without_llm['stats']

        print("指标对比:")
        print(f"  {'指标':<30} {'LLM模式':<15} {'Mock模式':<15}")
        print(f"  {'-'*60}")
        print(f"  {'LLM源码分析修复':<30} {stats_llm.get('fixed_by_source_analysis', 0):<15} {stats_mock.get('fixed_by_source_analysis', 0):<15}")
        print(f"  {'规则修复':<30} {stats_llm.get('fixed_by_rules', 0):<15} {stats_mock.get('fixed_by_rules', 0):<15}")
        print(f"  {'未修复':<30} {stats_llm.get('unfixed', 0):<15} {stats_mock.get('unfixed', 0):<15}")

        llm_advantage = stats_llm.get('fixed_by_source_analysis', 0)
        if llm_advantage > 0:
            print(f"\n✨ LLM源码分析成功修复了 {llm_advantage} 个Mock无法修复的断裂！")
        else:
            print(f"\n⚠️  这个案例中LLM没有展现优势，可能是：")
            print(f"   1. 没有遇到需要源码分析的断裂")
            print(f"   2. 所有断裂都被Mock数据覆盖了")

    print("\n" + "="*80)
    print("测试完成")
    print("="*80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
