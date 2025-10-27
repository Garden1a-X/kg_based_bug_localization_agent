#!/usr/bin/env python3
"""
检查知识图谱中函数实体是否包含源码信息
"""

import json

def check_function_entity_structure():
    """检查函数实体的字段结构"""
    print("="*80)
    print("检查函数实体结构")
    print("="*80)

    entity_file = "/data/xuao/code_kg_search/linux_test/data/temp_en.json"

    print(f"\n正在读取: {entity_file}")
    with open(entity_file, 'r') as f:
        entities = json.load(f)

    print(f"共有 {len(entities):,} 个实体\n")

    # 找几个MMC相关的函数实体
    print("查找MMC相关函数实体...\n")

    target_functions = [
        'mmc_schedule_delayed_work',
        'mmc_rescan',
        'mmc_alloc_host',
        'dw_mci_probe'
    ]

    found_functions = {}

    for entity in entities:
        if entity.get('type') == 'FUNCTION':
            name = entity.get('name', '')
            if name in target_functions:
                found_functions[name] = entity

                print("="*80)
                print(f"函数: {name}")
                print("="*80)
                print("字段列表:")
                for key in sorted(entity.keys()):
                    value = entity[key]
                    if isinstance(value, str) and len(value) > 200:
                        print(f"  {key}: (字符串, 长度={len(value)})")
                        print(f"       前100字符: {value[:100]}...")
                    else:
                        print(f"  {key}: {value}")
                print()

        if len(found_functions) >= len(target_functions):
            break

    print("\n" + "="*80)
    print("总结")
    print("="*80)

    if found_functions:
        print(f"\n找到 {len(found_functions)} 个目标函数")

        # 检查哪些字段可能包含源码
        all_fields = set()
        for entity in found_functions.values():
            all_fields.update(entity.keys())

        print(f"\n所有字段: {sorted(all_fields)}")

        # 检查可能的源码字段
        code_fields = ['code', 'body', 'source', 'content', 'definition', 'implementation']
        available_code_fields = [f for f in code_fields if f in all_fields]

        if available_code_fields:
            print(f"\n✅ 可能包含源码的字段: {available_code_fields}")
        else:
            print(f"\n❌ 未找到明显的源码字段")
            print(f"   需要检查是否有其他字段包含代码内容")
    else:
        print("\n❌ 未找到任何目标函数")

    # 额外检查：看看是否有source_file字段
    if found_functions:
        print("\n检查源文件信息:")
        for name, entity in found_functions.items():
            source_file = entity.get('source_file', 'N/A')
            print(f"  {name}: {source_file}")

if __name__ == "__main__":
    check_function_entity_structure()
