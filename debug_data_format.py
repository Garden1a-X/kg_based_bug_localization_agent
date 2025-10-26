#!/usr/bin/env python3
"""
调试脚本：查看知识图谱数据的实际格式
"""
import json
from pathlib import Path

data_dir = Path("/data/xuao/code_kg_search/linux_test/data")
entity_file = data_dir / "temp_en.json"
relation_file = data_dir / "relations.json"

print("=" * 80)
print("查看知识图谱数据格式")
print("=" * 80)

# ==================== 1. 查看实体文件结构 ====================
print("\n【1】实体文件结构")
print("-" * 80)

with open(entity_file, 'r', encoding='utf-8') as f:
    entities = json.load(f)

print(f"顶层类型: {type(entities).__name__}")

if isinstance(entities, dict):
    print(f"顶层键: {list(entities.keys())}")
    print(f"\n各类型实体数量:")
    for entity_type, entity_list in entities.items():
        if isinstance(entity_list, list):
            print(f"  {entity_type}: {len(entity_list)} 个")

    # 如果是字典格式，查看 FUNCTION
    if 'FUNCTION' in entities and entities['FUNCTION']:
        print("\n【2】FUNCTION 实体示例（前3个）")
        print("-" * 80)
        for i, func in enumerate(entities['FUNCTION'][:3], 1):
            print(f"\n示例 {i}:")
            print(json.dumps(func, indent=2, ensure_ascii=False))

elif isinstance(entities, list):
    print(f"列表长度: {len(entities)}")

    # 统计实体类型
    from collections import Counter
    type_counter = Counter()
    for entity in entities:
        if isinstance(entity, dict):
            entity_type = entity.get('type') or entity.get('label') or entity.get('entity_type') or 'UNKNOWN'
            type_counter[entity_type] += 1

    print(f"\n各类型实体数量:")
    for entity_type, count in type_counter.most_common():
        print(f"  {entity_type}: {count} 个")

    # ==================== 2. 查看 FUNCTION 实体示例 ====================
    print("\n【2】FUNCTION 实体示例（前3个）")
    print("-" * 80)

    function_count = 0
    for entity in entities:
        if isinstance(entity, dict):
            entity_type = entity.get('type') or entity.get('label') or entity.get('entity_type')
            if entity_type == 'FUNCTION':
                function_count += 1
                if function_count <= 3:
                    print(f"\n示例 {function_count}:")
                    print(json.dumps(entity, indent=2, ensure_ascii=False))
                if function_count >= 3:
                    break

# ==================== 3. 搜索 MMC 相关函数 ====================
print("\n【3】搜索 MMC 相关函数")
print("-" * 80)

mmc_functions = []
all_functions = []

# 适配两种格式
if isinstance(entities, dict) and 'FUNCTION' in entities:
    function_list = entities['FUNCTION']
elif isinstance(entities, list):
    function_list = [e for e in entities if isinstance(e, dict) and
                     (e.get('type') == 'FUNCTION' or e.get('label') == 'FUNCTION' or e.get('entity_type') == 'FUNCTION')]
else:
    function_list = []

for func in function_list:
    if isinstance(func, dict) and 'name' in func:
        name = func['name']
        all_functions.append(name)
        if 'mmc' in name.lower() or 'dw_mci' in name.lower():
            mmc_functions.append(name)
            if len(mmc_functions) <= 10:  # 只打印前10个
                print(f"  - {name}")

print(f"\n总共找到 {len(mmc_functions)} 个 MMC 相关函数")
print(f"总函数数: {len(all_functions)}")

# 特别搜索我们需要的两个函数
print("\n【4】搜索特定函数")
print("-" * 80)
target_funcs = ['dw_mci_pltfm_probe', 'dw_mci_execute_tuning']

for target in target_funcs:
    found = False
    for func in function_list:
        if isinstance(func, dict) and func.get('name') == target:
            print(f"\n✓ 找到: {target}")
            print(json.dumps(func, indent=2, ensure_ascii=False))
            found = True
            break

    if not found:
        print(f"\n✗ 未找到: {target}")
        # 尝试模糊搜索
        similar = [f['name'] for f in function_list
                  if isinstance(f, dict) and 'name' in f and target[:10] in f['name']]
        if similar:
            print(f"  相似的函数名: {similar[:5]}")

# ==================== 5. 查看 CALLS 关系示例 ====================
print("\n【5】CALLS 关系示例（前3个）")
print("-" * 80)

with open(relation_file, 'r', encoding='utf-8') as f:
    relations = json.load(f)

print(f"关系数据类型: {type(relations).__name__}")

calls_list = []

# 适配两种格式
if isinstance(relations, dict) and 'CALLS' in relations:
    calls_list = relations['CALLS'][:3]
elif isinstance(relations, list):
    # 从列表中找出 CALLS 类型的关系
    for rel in relations:
        if isinstance(rel, dict):
            rel_type = rel.get('type') or rel.get('label') or rel.get('relation_type')
            if rel_type == 'CALLS':
                calls_list.append(rel)
                if len(calls_list) >= 3:
                    break

if calls_list:
    for i, rel in enumerate(calls_list, 1):
        print(f"\n示例 {i}:")
        print(json.dumps(rel, indent=2, ensure_ascii=False))
else:
    print("未找到 CALLS 关系！")

# 统计关系类型
print("\n【6】关系类型统计")
print("-" * 80)

if isinstance(relations, dict):
    print("关系以字典格式组织:")
    for rel_type, rel_list in relations.items():
        if isinstance(rel_list, list):
            print(f"  {rel_type}: {len(rel_list)} 个")
elif isinstance(relations, list):
    print("关系以列表格式组织:")
    from collections import Counter
    rel_type_counter = Counter()
    for rel in relations:
        if isinstance(rel, dict):
            rel_type = rel.get('type') or rel.get('label') or rel.get('relation_type') or 'UNKNOWN'
            rel_type_counter[rel_type] += 1

    for rel_type, count in rel_type_counter.most_common():
        print(f"  {rel_type}: {count} 个")

print("\n" + "=" * 80)
print("调试完成！")
print("=" * 80)
