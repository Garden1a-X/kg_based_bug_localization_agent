#!/usr/bin/env python3
"""
快速测试 ID 类型修复
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.kg_interface import KnowledgeGraphInterface

print("=" * 80)
print("测试 ID 类型修复")
print("=" * 80)

# 初始化
data_dir = "/data/xuao/code_kg_search/linux_test/data"
kg = KnowledgeGraphInterface(data_dir)

# 测试关键函数的 callees
test_functions = [
    "dw_mci_pltfm_probe",
    "dw_mci_pltfm_register",
    "dw_mci_probe"
]

print("\n【测试 get_callees】")
print("-" * 80)

for func_name in test_functions:
    func_entity = kg.find_function(func_name)
    if func_entity:
        func_id = func_entity.get('id')
        print(f"\n✓ {func_name}")
        print(f"  ID: {func_id} (type: {type(func_id).__name__})")

        callees = kg.get_callees(func_name)
        print(f"  被调用函数数量: {len(callees)}")
        if callees:
            print(f"  前3个被调用函数: {', '.join(callees[:3])}")
    else:
        print(f"\n✗ {func_name} - 未找到")

# 测试路径搜索
print("\n" + "=" * 80)
print("【测试路径搜索】")
print("-" * 80)

start_func = "dw_mci_pltfm_probe"
end_func = "dw_mci_execute_tuning"

print(f"\n查找路径: {start_func} -> {end_func}")

result = kg.find_call_path_with_indirect(start_func, end_func, max_depth=15, debug=False)

if result and result['path']:
    print(f"\n✓ 找到路径！长度: {len(result['path'])}")
    print(f"\n路径:")
    for i, node in enumerate(result['path'], 1):
        edge_info = ""
        if i - 1 < len(result.get('edges', [])):
            edge = result['edges'][i - 1]
            if isinstance(edge, dict):
                edge_info = f" [{edge.get('type', 'unknown')}]"
            else:
                edge_info = f" [{edge}]"
        print(f"  {i}. {node}{edge_info}")

    # 统计边类型
    edges = result.get('edges', [])
    direct_count = sum(1 for e in edges if e == 'direct')
    indirect_count = sum(1 for e in edges if isinstance(e, dict))

    print(f"\n统计:")
    print(f"  直接调用: {direct_count}")
    print(f"  间接调用: {indirect_count}")
else:
    print(f"\n✗ 未找到路径")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)

kg.close()
