#!/usr/bin/env python3
"""
检查间接调用关系
"""
from data.kg_interface import KnowledgeGraphInterface

print("=" * 80)
print("检查间接调用关系")
print("=" * 80)

data_dir = "/data/xuao/code_kg_search/linux_test/data"
kg = KnowledgeGraphInterface(data_dir)

# 目标函数
target_func = "dw_mci_execute_tuning"
target_entity = kg.find_function(target_func)

if not target_entity:
    print(f"✗ 函数不存在: {target_func}")
    exit(1)

target_id = target_entity['id']
print(f"\n【1】目标函数: {target_func} (id: {target_id})")
print("-" * 80)

# 查找所有指向这个函数的 ASSIGNED_TO 关系
print(f"\n【2】查找 ASSIGNED_TO 关系")
print("哪些实体被赋值为这个函数？")

assigned_count = 0
if 'ASSIGNED_TO' in kg.relations:
    for rel in kg.relations['ASSIGNED_TO']:
        tail = rel.get('tail')
        if tail == target_id:
            head = rel.get('head')
            head_entity = kg.entity_by_id.get(head)

            assigned_count += 1
            if assigned_count <= 10:  # 只显示前10个
                if head_entity:
                    print(f"  {assigned_count}. {head_entity.get('name', 'N/A')} (type: {head_entity.get('type', 'N/A')})")
                    # 如果是 FIELD，显示更多信息
                    if head_entity.get('type') == 'FIELD':
                        print(f"      -> 这是一个结构体字段！")
                else:
                    print(f"  {assigned_count}. ID={head} (实体未找到)")

print(f"\n总共找到 {assigned_count} 个 ASSIGNED_TO 关系")

# 查找 mmc_rescan 相关的异步挂载
print(f"\n【3】查找 mmc_rescan 的工作队列挂载")
print("-" * 80)

rescan_entity = kg.find_function("mmc_rescan")
if rescan_entity:
    rescan_id = rescan_entity['id']
    print(f"✓ 找到 mmc_rescan (id: {rescan_id})")

    print("\n查找被赋值为 mmc_rescan 的实体:")
    rescan_assigned = 0
    if 'ASSIGNED_TO' in kg.relations:
        for rel in kg.relations['ASSIGNED_TO']:
            tail = rel.get('tail')
            if tail == rescan_id:
                head = rel.get('head')
                head_entity = kg.entity_by_id.get(head)

                rescan_assigned += 1
                if rescan_assigned <= 5:
                    if head_entity:
                        print(f"  {rescan_assigned}. {head_entity.get('name', 'N/A')} (type: {head_entity.get('type', 'N/A')})")
                        if 'detect' in head_entity.get('name', '').lower():
                            print(f"      -> 可能是 host->detect！")

    print(f"\n总共 {rescan_assigned} 个赋值")
else:
    print("✗ 未找到 mmc_rescan")

# 统计 ASSIGNED_TO 关系
print(f"\n【4】ASSIGNED_TO 关系统计")
print("-" * 80)
if 'ASSIGNED_TO' in kg.relations:
    total = len(kg.relations['ASSIGNED_TO'])
    print(f"总数: {total}")

    # 统计目标类型
    from collections import Counter
    tail_types = Counter()
    for rel in kg.relations['ASSIGNED_TO'][:10000]:  # 采样前1万个
        tail = rel.get('tail')
        tail_entity = kg.entity_by_id.get(tail)
        if tail_entity:
            tail_types[tail_entity.get('type', 'UNKNOWN')] += 1

    print("\n被赋值的实体类型分布（采样）:")
    for entity_type, count in tail_types.most_common(10):
        print(f"  {entity_type}: {count}")

kg.close()

print("\n" + "=" * 80)
print("检查完成！")
print("=" * 80)
