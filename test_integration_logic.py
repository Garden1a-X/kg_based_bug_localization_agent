#!/usr/bin/env python3
"""
测试LLM源码分析集成的逻辑（使用Mock数据）
验证CallChainTracerAgent的分层回退机制
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_integration_logic():
    """测试集成逻辑（不依赖真实数据）"""

    print("="*80)
    print("测试：LLM源码分析集成逻辑（Mock模式）")
    print("="*80)

    # 创建Mock的KG和LLM
    print("\n[1/3] 创建Mock组件...")

    mock_kg = Mock()
    mock_llm = Mock()

    # 模拟函数查询返回结果
    mock_kg.get_function_ids.side_effect = lambda name: {
        'mmc_schedule_delayed_work': ['func_1'],
        'mmc_rescan': ['func_2']
    }.get(name, [])

    # 模拟函数信息
    mock_kg.get_function_info.side_effect = lambda fid: {
        'func_1': {
            'id': 'func_1',
            'name': 'mmc_schedule_delayed_work',
            'source_file': 'E:\\cpppro\\clang_kg\\linux\\drivers\\mmc\\core\\core.c',
            'start_line': 100,
            'end_line': 120
        },
        'func_2': {
            'id': 'func_2',
            'name': 'mmc_rescan',
            'source_file': 'E:\\cpppro\\clang_kg\\linux\\drivers\\mmc\\core\\core.c',
            'start_line': 200,
            'end_line': 250
        }
    }.get(fid, None)

    # Mock KG的异步检查（返回None表示没有Mock数据）
    mock_kg.check_async_pattern.return_value = None

    print("  ✓ Mock KG创建完成")
    print("  ✓ Mock LLM创建完成")

    # 导入Agent类
    print("\n[2/3] 导入CallChainTracerAgent...")
    from agents.chain_tracer_agent import CallChainTracerAgent

    # 创建Agent实例
    agent = CallChainTracerAgent(kg=mock_kg, llm_client=mock_llm)

    print(f"  ✓ Agent创建完成")
    print(f"  - bridge_finder存在: {agent.bridge_finder is not None}")
    print(f"  - source_reader存在: {agent.source_reader is not None}")

    # 测试分层回退机制
    print("\n[3/3] 测试分层回退机制...")
    print("\n场景1: bridge_finder.find_bridge_between_functions 返回结果")
    print("-" * 80)

    # Mock bridge_finder返回成功结果
    mock_bridge_result = {
        'bridge_type': 'async_work',
        'bridge_entity': 'host->detect',
        'confidence': 1.0,
        'explanation': 'LLM analysis found connection through host->detect'
    }
    agent.bridge_finder.find_bridge_between_functions = Mock(return_value=mock_bridge_result)

    result1 = agent._check_async_pattern('mmc_schedule_delayed_work', 'mmc_rescan')

    if result1:
        print("✅ Layer 1成功: 使用了LLM源码分析")
        print(f"  方法: {result1.get('method')}")
        print(f"  桥接类型: {result1.get('bridge_type')}")
        print(f"  桥接实体: {result1.get('bridge_entity')}")
        print(f"  置信度: {result1.get('confidence')}")
        assert result1['method'] == 'llm_source_analysis', "应该使用llm_source_analysis方法"
        assert agent.stats['fixed_by_source_analysis'] == 1, "统计应该增加"
    else:
        print("❌ Layer 1失败")

    print("\n场景2: bridge_finder返回None，回退到Mock")
    print("-" * 80)

    # Mock bridge_finder返回None
    agent.bridge_finder.find_bridge_between_functions = Mock(return_value=None)

    # Mock KG返回Mock数据
    mock_kg.check_async_pattern.return_value = {
        'bridge_type': 'async',
        'init_func': 'mmc_alloc_host',
        'bridge_entity': 'host->detect'
    }

    result2 = agent._check_async_pattern('mmc_schedule_delayed_work', 'mmc_rescan')

    if result2:
        print("✅ Layer 2成功: 回退到Mock数据")
        print(f"  桥接类型: {result2.get('bridge_type')}")
        print(f"  初始化函数: {result2.get('init_func')}")
    else:
        print("❌ Layer 2失败")

    print("\n场景3: 没有bridge_finder（旧版本兼容）")
    print("-" * 80)

    # 创建没有LLM的Agent
    agent_no_llm = CallChainTracerAgent(kg=mock_kg, llm_client=None)

    print(f"  bridge_finder存在: {agent_no_llm.bridge_finder is not None}")

    result3 = agent_no_llm._check_async_pattern('mmc_schedule_delayed_work', 'mmc_rescan')

    if result3:
        print("✅ 兼容性测试通过: 直接使用Mock数据")
        print(f"  桥接类型: {result3.get('bridge_type')}")
    else:
        print("❌ 兼容性测试失败")

    # 汇总统计
    print("\n" + "="*80)
    print("统计信息")
    print("="*80)
    for key, value in agent.stats.items():
        print(f"  {key}: {value}")

    # 验证结果
    print("\n" + "="*80)
    print("验证结果")
    print("="*80)

    success = True

    if result1 and result1['method'] == 'llm_source_analysis':
        print("✅ Layer 1 (LLM源码分析) 工作正常")
    else:
        print("❌ Layer 1 (LLM源码分析) 失败")
        success = False

    if result2:
        print("✅ Layer 2 (Mock回退) 工作正常")
    else:
        print("❌ Layer 2 (Mock回退) 失败")
        success = False

    if agent_no_llm.bridge_finder is None and result3:
        print("✅ 向后兼容性 工作正常")
    else:
        print("❌ 向后兼容性 失败")
        success = False

    return success


def main():
    try:
        print("开始集成逻辑测试...\n")

        success = test_integration_logic()

        print("\n" + "="*80)
        print("测试完成")
        print("="*80)

        if success:
            print("\n✅ 所有集成逻辑测试通过!")
            print("\n总结:")
            print("  1. LLM源码分析作为第一层尝试（优先级最高）")
            print("  2. Mock数据作为第二层回退")
            print("  3. 向后兼容没有LLM的情况")
            print("\n集成完成，可以在真实环境中运行完整测试。")
        else:
            print("\n❌ 部分测试失败")

    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
