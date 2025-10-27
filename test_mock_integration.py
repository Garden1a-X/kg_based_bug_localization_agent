#!/usr/bin/env python3
"""
测试 mock 数据集成
验证间接调用关系的检测和修复
"""
from data.kg_interface import KnowledgeGraphInterface
from agents.chain_tracer_agent import CallChainTracerAgent

print("=" * 80)
print("测试 Mock 数据集成")
print("=" * 80)

# 初始化
data_dir = "/data/xuao/code_kg_search/linux_test/data"
kg = KnowledgeGraphInterface(data_dir)

print("\n【1】测试 Mock 数据访问")
print("-" * 80)

# 测试异步调用检测
print("\n测试1: 异步调用检测")
print("  检查: mmc_schedule_delayed_work -> mmc_rescan")
async_bridge = kg.check_async_pattern("mmc_schedule_delayed_work", "mmc_rescan")
if async_bridge:
    print(f"  ✓ 检测到异步桥接:")
    print(f"    - 类型: {async_bridge.get('bridge_type')}")
    print(f"    - 实体: {async_bridge.get('bridge_entity')}")
    print(f"    - 初始化: {async_bridge.get('init_func')}")
    print(f"    - 说明: {async_bridge.get('description', 'N/A')}")
else:
    print("  ✗ 未检测到异步桥接")

# 测试函数指针检测
print("\n测试2: 函数指针检测")
print("  检查: mmc_rescan -> dw_mci_execute_tuning")
fp_bridge = kg.check_function_pointer_pattern("mmc_rescan", "dw_mci_execute_tuning")
if fp_bridge:
    print(f"  ✓ 检测到函数指针桥接:")
    print(f"    - 类型: {fp_bridge.get('bridge_type')}")
    print(f"    - 实体: {fp_bridge.get('bridge_entity')}")
    print(f"    - 结构体: {fp_bridge.get('struct_name', 'N/A')}")
    print(f"    - 字段: {fp_bridge.get('field_name', 'N/A')}")
    print(f"    - 说明: {fp_bridge.get('description', 'N/A')}")
else:
    print("  ✗ 未检测到函数指针桥接")

print("\n【2】测试调用链追踪（包含间接调用）")
print("-" * 80)

# 查找起止函数
start_func = "mmc_add_host"
end_func = "dw_mci_execute_tuning"

start_entity = kg.find_function(start_func)
end_entity = kg.find_function(end_func)

if not start_entity:
    print(f"✗ 起始函数不存在: {start_func}")
elif not end_entity:
    print(f"✗ 目标函数不存在: {end_func}")
else:
    print(f"✓ 起始函数: {start_func}")
    print(f"✓ 目标函数: {end_func}")

    # 测试部分路径（到第一个断点之前）
    print("\n测试3: 查找到 mmc_schedule_delayed_work 的路径")
    intermediate = "mmc_schedule_delayed_work"
    path_to_async = kg.find_call_path(start_func, intermediate, max_depth=20)

    if path_to_async:
        print(f"  ✓ 找到路径，长度: {len(path_to_async)}")
        print(f"  路径: {' -> '.join(path_to_async)}")

        # 检查断点
        has_break = False
        for i in range(len(path_to_async) - 1):
            if not kg.has_direct_call(path_to_async[i], path_to_async[i+1]):
                has_break = True
                print(f"  ⚠ 断点: {path_to_async[i]} -/-> {path_to_async[i+1]}")

        if not has_break:
            print("  ✓ 路径完整，无断点")
    else:
        print(f"  ✗ 未找到路径")

    # 测试完整路径（使用 chain tracer）
    print("\n测试4: 使用 ChainTracerAgent")
    tracer = CallChainTracerAgent(kg)

    # 尝试追踪到 mmc_rescan（包含第一个断点）
    print(f"\n  追踪: {start_func} -> mmc_rescan")
    mmc_rescan_entity = kg.find_function("mmc_rescan")
    if mmc_rescan_entity:
        result = tracer.execute(start_entity, mmc_rescan_entity, max_depth=20)

        print(f"\n  结果:")
        print(f"    - 成功: {result['success']}")
        print(f"    - 路径长度: {len(result['path'])}")
        print(f"    - 断点数量: {len(result['breaks'])}")

        if result['path']:
            print(f"\n  修复后的路径:")
            for i, node in enumerate(result['path'], 1):
                print(f"    {i}. {node}")

        if result['breaks']:
            print(f"\n  断点详情:")
            for i, brk in enumerate(result['breaks'], 1):
                fixed_mark = "✓" if brk['fixed'] else "✗"
                print(f"    {i}. {fixed_mark} {brk['from']} -> {brk['to']}")
                if brk['fixed']:
                    print(f"       方法: {brk['method']}")
                    if brk['bridge']:
                        print(f"       桥接: {brk['bridge'].get('bridge_entity', 'N/A')}")

        print(f"\n  统计:")
        stats = result['stats']
        print(f"    - 总断点: {stats['total_breaks']}")
        print(f"    - 规则修复: {stats['fixed_by_rules']}")
        print(f"    - LLM修复: {stats['fixed_by_llm']}")
        print(f"    - 未修复: {stats['unfixed']}")

print("\n【3】总结")
print("-" * 80)
print("Mock 数据集成测试完成！")
print("\n预期结果:")
print("  1. ✓ 检测到异步调用桥接（mmc_schedule_delayed_work -> mmc_rescan）")
print("  2. ✓ 检测到函数指针桥接（mmc_rescan -> dw_mci_execute_tuning）")
print("  3. ✓ ChainTracerAgent 能够使用 mock 数据修复断点")
print("\n" + "=" * 80)

kg.close()
