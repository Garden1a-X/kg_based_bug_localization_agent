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

# ==================== 2. 查看 FUNCTION 实体示例 ====================
print("\n【2】FUNCTION 实体示例（前3个）")
print("-" * 80)

if 'FUNCTION' in entities and entities['FUNCTION']:
    for i, func in enumerate(entities['FUNCTION'][:3], 1):
        print(f"\n示例 {i}:")
        print(json.dumps(func, indent=2, ensure_ascii=False))

# ==================== 3. 搜索 MMC 相关函数 ====================
print("\n【3】搜索 MMC 相关函数")
print("-" * 80)

if 'FUNCTION' in entities:
    mmc_functions = []
    for func in entities['FUNCTION']:
        if isinstance(func, dict) and 'name' in func:
            name = func['name']
            if 'mmc' in name.lower() or 'dw_mci' in name.lower():
                mmc_functions.append(name)
                if len(mmc_functions) <= 10:  # 只打印前10个
                    print(f"  - {name}")

    print(f"\n总共找到 {len(mmc_functions)} 个 MMC 相关函数")

    # 特别搜索我们需要的两个函数
    print("\n【4】搜索特定函数")
    print("-" * 80)
    target_funcs = ['dw_mci_pltfm_probe', 'dw_mci_execute_tuning']

    for target in target_funcs:
        found = False
        for func in entities['FUNCTION']:
            if isinstance(func, dict) and func.get('name') == target:
                print(f"\n✓ 找到: {target}")
                print(json.dumps(func, indent=2, ensure_ascii=False))
                found = True
                break

        if not found:
            print(f"\n✗ 未找到: {target}")
            # 尝试模糊搜索
            similar = [f['name'] for f in entities['FUNCTION']
                      if isinstance(f, dict) and 'name' in f and target[:10] in f['name']]
            if similar:
                print(f"  相似的函数名: {similar[:5]}")

# ==================== 5. 查看 CALLS 关系示例 ====================
print("\n【5】CALLS 关系示例（前3个）")
print("-" * 80)

with open(relation_file, 'r', encoding='utf-8') as f:
    relations = json.load(f)

if 'CALLS' in relations and relations['CALLS']:
    for i, rel in enumerate(relations['CALLS'][:3], 1):
        print(f"\n示例 {i}:")
        print(json.dumps(rel, indent=2, ensure_ascii=False))

print("\n" + "=" * 80)
print("调试完成！")
print("=" * 80)
