#!/usr/bin/env python3
"""
测试MasterCoordinator集成子图自动选择功能

测试场景：
1. 启用子图自动选择 - 应该基于日志内容自动选择MMC子图
2. 手动指定子图 - 跳过自动选择，直接使用指定的子图
3. 不启用子图选择 - 使用默认行为
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from coordinator.master_coordinator import MasterCoordinator
from llm import LLMClient


def test_automatic_subgraph_selection():
    """测试自动子图选择"""
    print("=" * 80)
    print("测试用例 1: 自动子图选择（基于MMC错误日志）")
    print("=" * 80)

    # MMC tuning错误日志
    mmc_log = """
[    3.668283] mmc0: tuning execution failed: -5
[    3.668290] mmc0: error -5 whilst initialising SD card
[    3.668293] dwmmc_k3 ff3fb000.dwmmc0: mmc0: hi3660_execute_tuning failed
"""

    # 创建LLM客户端
    llm_config = {
        'backend': 'openai',
        'model': 'gpt-4o-mini',
        'base_url': 'http://10.12.208.86:8502',
        'api_key': ''
    }

    # 创建协调器，启用子图选择
    coordinator = MasterCoordinator(
        data_dir='/data/xuao/code_kg_search/linux_test/data',
        enable_llm_detection=True,
        enable_llm_log_analysis=True,
        enable_subgraph_selection=True,  # 启用子图自动选择
        llm_config=llm_config
    )

    print("\n启动分析流程...")
    print("期望：LLM应该自动选择 'mmc' 子图\n")

    try:
        # 处理日志（会自动选择子图）
        result = coordinator.process(mmc_log)

        print("\n" + "=" * 80)
        print("测试结果")
        print("=" * 80)

        if result['success']:
            print("✅ 分析成功完成")
            print(f"   调用链长度: {result['chain']['length']}")
            print(f"   总断点数: {result['chain']['stats']['total_breaks']}")
            print(f"   已修复: {result['chain']['stats']['fixed_by_rules'] + result['chain']['stats'].get('fixed_by_source_analysis', 0) + result['chain']['stats']['fixed_by_llm']}")
        else:
            print("⚠️  分析部分成功或失败")
            if 'error' in result:
                print(f"   错误: {result['error']}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        coordinator.close()


def test_manual_subgraph_override():
    """测试手动指定子图"""
    print("\n\n" + "=" * 80)
    print("测试用例 2: 手动指定子图（强制使用mmc子图）")
    print("=" * 80)

    mmc_log = """
[    3.668283] mmc0: tuning execution failed: -5
[    3.668290] mmc0: error -5 whilst initialising SD card
"""

    llm_config = {
        'backend': 'openai',
        'model': 'gpt-4o-mini',
        'base_url': 'http://10.12.208.86:8502',
        'api_key': ''
    }

    # 创建协调器，启用子图选择
    coordinator = MasterCoordinator(
        data_dir='/data/xuao/code_kg_search/linux_test/data',
        enable_llm_detection=True,
        enable_llm_log_analysis=True,
        enable_subgraph_selection=True,
        llm_config=llm_config
    )

    print("\n启动分析流程...")
    print("期望：跳过LLM选择，直接使用手动指定的 'mmc' 子图\n")

    try:
        # 手动指定子图
        result = coordinator.process(mmc_log, subgraph_override='mmc')

        print("\n" + "=" * 80)
        print("测试结果")
        print("=" * 80)

        if result['success']:
            print("✅ 分析成功完成")
            print(f"   调用链长度: {result['chain']['length']}")
        else:
            print("⚠️  分析部分成功或失败")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        coordinator.close()


def test_without_subgraph_selection():
    """测试不启用子图选择（使用默认行为）"""
    print("\n\n" + "=" * 80)
    print("测试用例 3: 不启用子图选择（使用默认行为）")
    print("=" * 80)

    mmc_log = """
[    3.668283] mmc0: tuning execution failed: -5
[    3.668290] mmc0: error -5 whilst initialising SD card
"""

    llm_config = {
        'backend': 'openai',
        'model': 'gpt-4o-mini',
        'base_url': 'http://10.12.208.86:8502',
        'api_key': ''
    }

    # 创建协调器，不启用子图选择
    coordinator = MasterCoordinator(
        data_dir='/data/xuao/code_kg_search/linux_test/data/mmc',  # 直接指定mmc目录
        enable_llm_detection=True,
        enable_llm_log_analysis=True,
        enable_subgraph_selection=False,  # 不启用子图选择
        llm_config=llm_config
    )

    print("\n启动分析流程...")
    print("期望：直接使用data_dir指定的图谱，不进行子图选择\n")

    try:
        result = coordinator.process(mmc_log)

        print("\n" + "=" * 80)
        print("测试结果")
        print("=" * 80)

        if result['success']:
            print("✅ 分析成功完成")
            print(f"   调用链长度: {result['chain']['length']}")
        else:
            print("⚠️  分析部分成功或失败")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        coordinator.close()


def main():
    """运行所有测试"""
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "MasterCoordinator子图选择集成测试" + " " * 23 + "║")
    print("╚" + "═" * 78 + "╝")

    # 测试1：自动选择
    test_automatic_subgraph_selection()

    # 测试2：手动指定
    test_manual_subgraph_override()

    # 测试3：不启用子图选择
    test_without_subgraph_selection()

    print("\n\n" + "=" * 80)
    print("所有测试完成！")
    print("=" * 80)


if __name__ == '__main__':
    main()
