#!/usr/bin/env python3
"""
查找正确的起点函数
找一个确实调用了其他函数的入口点
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.kg_interface import KnowledgeGraphInterface

print("=" * 80)
print("查找正确的起点函数")
print("=" * 80)

data_dir = "/data/xuao/code_kg_search/linux_test/data"
kg = KnowledgeGraphInterface(data_dir)

# 候选起点函数（MMC相关的入口点）
candidates = [
    "mmc_add_host",
    "mmc_alloc_host",
    "dw_mci_probe",
    "dw_mci_pltfm_probe",
    "dw_mci_common_probe",
]

print("\n检查候选起点函数的调用关系:\n")

for func_name in candidates:
    func = kg.find_function(func_name)
    if not func:
        print(f"✗ {func_name}: 不存在")
        continue

    callees = kg.get_callees(func_name)
    callers = kg.get_callers(func_name)

    print(f"{'✓' if callees else '✗'} {func_name}:")
    print(f"   调用: {len(callees)} 个函数")
    print(f"   被调用: {len(callers)} 次")
    if callees:
        print(f"   前3个被调用函数: {callees[:3]}")
    print()

# 尝试找到能到达 mmc_schedule_delayed_work 的函数
print("\n" + "=" * 80)
print("查找能调用 mmc_schedule_delayed_work 的函数")
print("=" * 80 + "\n")

target = "mmc_schedule_delayed_work"
callers = kg.get_callers(target)
print(f"{target} 的调用者: {len(callers)} 个")
if callers:
    print(f"前10个: {callers[:10]}")

# 递归向上查找
print("\n继续向上追溯这些调用者的调用者:")
for caller in callers[:3]:
    upper_callers = kg.get_callers(caller)
    print(f"\n{caller} 被调用 {len(upper_callers)} 次")
    if upper_callers:
        print(f"  调用者: {upper_callers[:5]}")

kg.close()
