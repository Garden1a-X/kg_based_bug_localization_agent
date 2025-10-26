#!/usr/bin/env python3
"""
测试调用链查找
"""
from data.kg_interface import KnowledgeGraphInterface

print("=" * 80)
print("测试调用链查找")
print("=" * 80)

# 创建接口
data_dir = "/data/xuao/code_kg_search/linux_test/data"
kg = KnowledgeGraphInterface(data_dir)

# 测试函数
start_func = "dw_mci_pltfm_probe"
end_func = "dw_mci_execute_tuning"

print(f"\n查找路径: {start_func} -> {end_func}")
print("-" * 80)

# 1. 检查函数是否存在
print("\n【1】检查函数是否存在")
start_entity = kg.find_function(start_func)
end_entity = kg.find_function(end_func)

if start_entity:
    print(f"✓ 起点函数存在: {start_entity['name']} (id: {start_entity.get('id')})")
else:
    print(f"✗ 起点函数不存在")

if end_entity:
    print(f"✓ 终点函数存在: {end_entity['name']} (id: {end_entity.get('id')})")
else:
    print(f"✗ 终点函数不存在")

# 2. 查看起点的直接调用
print(f"\n【2】起点 {start_func} 直接调用的函数（前10个）")
callees = kg.get_callees(start_func)
print(f"共调用 {len(callees)} 个函数:")
for i, callee in enumerate(callees[:10], 1):
    print(f"  {i}. {callee}")

# 3. 查看终点被谁调用
print(f"\n【3】终点 {end_func} 被谁调用（前10个）")
callers = kg.get_callers(end_func)
print(f"共被 {len(callers)} 个函数调用:")
for i, caller in enumerate(callers[:10], 1):
    print(f"  {i}. {caller}")

# 4. 查找路径（多个深度）
print(f"\n【4】尝试不同深度查找路径")
for depth in [5, 10, 15, 20]:
    print(f"\n  深度 {depth}:")
    path = kg.find_call_path(start_func, end_func, max_depth=depth)
    if path:
        print(f"    ✓ 找到路径，长度: {len(path)}")
        print(f"    路径: {' -> '.join(path[:5])}{'...' if len(path) > 5 else ''}")
        break
    else:
        print(f"    ✗ 未找到")

# 5. 检查是否有共同的调用关系
print(f"\n【5】查找中间连接")
print("起点调用的函数中，是否有调用终点的？")
common_found = False
for callee in callees[:20]:  # 检查前20个
    callee_callees = kg.get_callees(callee)
    if end_func in callee_callees:
        print(f"  ✓ 找到2跳路径: {start_func} -> {callee} -> {end_func}")
        common_found = True
        break

if not common_found:
    print("  ✗ 前20个直接调用中未找到2跳路径")

# 6. 统计信息
print(f"\n【6】图谱统计")
stats = kg.get_database_stats()
print(f"  FUNCTION 实体数: {stats.get('FUNCTION', 0)}")
print(f"  CALLS 关系数: {stats.get('CALLS', 0)}")

kg.close()

print("\n" + "=" * 80)
print("测试完成！")
print("=" * 80)
