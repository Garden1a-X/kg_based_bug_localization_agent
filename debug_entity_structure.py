#!/usr/bin/env python3
"""
调试实体文件结构和查找缺失的实体ID
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

def debug_entity_file(entity_file, target_id):
    """调试实体文件结构"""
    print(f"调试实体文件: {entity_file}")
    print(f"查找目标ID: {target_id}")
    print("="*80)

    print("\n加载实体数据...")
    with open(entity_file, 'r') as f:
        data = json.load(f)

    # 1. 分析数据结构
    print(f"\n[1] 数据结构分析:")
    print(f"数据类型: {type(data)}")

    if isinstance(data, dict):
        print(f"顶层键: {list(data.keys())}")

        # 统计每个类型的实体数量
        print(f"\n实体类型统计:")
        for key, value in data.items():
            if isinstance(value, list):
                print(f"  {key}: {len(value)} 个")

    # 2. 全局搜索目标ID
    print(f"\n[2] 全局搜索 ID {target_id}:")
    found_locations = []

    def search_in_obj(obj, path="root"):
        """递归搜索对象中的ID"""
        if isinstance(obj, dict):
            if str(obj.get('id')) == str(target_id):
                found_locations.append((path, obj))
            for key, value in obj.items():
                search_in_obj(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                search_in_obj(item, f"{path}[{i}]")

    search_in_obj(data)

    if found_locations:
        print(f"✅ 找到 {len(found_locations)} 个匹配:")
        for path, entity in found_locations:
            print(f"\n  位置: {path}")
            print(f"  实体信息:")
            for key, value in entity.items():
                if key != 'code' and key != 'ast':
                    print(f"    {key}: {value}")
    else:
        print(f"❌ 未找到 ID {target_id}")

    # 3. 检查ID范围
    print(f"\n[3] ID范围分析:")
    all_ids = []

    def collect_ids(obj):
        if isinstance(obj, dict):
            if 'id' in obj:
                try:
                    all_ids.append(int(obj['id']))
                except:
                    pass
            for value in obj.values():
                collect_ids(value)
        elif isinstance(obj, list):
            for item in obj:
                collect_ids(item)

    collect_ids(data)

    if all_ids:
        all_ids.sort()
        print(f"  ID数量: {len(all_ids)}")
        print(f"  ID范围: {all_ids[0]} ~ {all_ids[-1]}")
        print(f"  目标ID {target_id} 在范围内: {all_ids[0] <= int(target_id) <= all_ids[-1]}")

        # 找最接近的ID
        target_int = int(target_id)
        closest_below = max([i for i in all_ids if i < target_int], default=None)
        closest_above = min([i for i in all_ids if i > target_int], default=None)

        if closest_below:
            print(f"  最接近的更小ID: {closest_below}")
        if closest_above:
            print(f"  最接近的更大ID: {closest_above}")

    return found_locations


def check_id_in_relations(relation_file, target_id):
    """检查ID在关系中的使用情况"""
    print(f"\n[4] 检查ID在关系中的使用:")
    print(f"加载关系数据...")

    with open(relation_file, 'r') as f:
        relations = json.load(f)

    # 作为head的关系
    as_head = [r for r in relations if str(r.get('head')) == str(target_id)]
    # 作为tail的关系
    as_tail = [r for r in relations if str(r.get('tail')) == str(target_id)]

    print(f"\n  作为源头(head): {len(as_head)} 条")
    if as_head:
        type_counts = defaultdict(int)
        for rel in as_head:
            type_counts[rel.get('type')] += 1
        for rel_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    - {rel_type}: {count}")

        print(f"\n  示例 (前5条):")
        for i, rel in enumerate(as_head[:5], 1):
            print(f"    [{i}] {rel}")

    print(f"\n  作为目标(tail): {len(as_tail)} 条")
    if as_tail:
        type_counts = defaultdict(int)
        for rel in as_tail:
            type_counts[rel.get('type')] += 1
        for rel_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    - {rel_type}: {count}")

        print(f"\n  示例 (前5条):")
        for i, rel in enumerate(as_tail[:5], 1):
            print(f"    [{i}] {rel}")


def sample_entity_types(entity_file):
    """采样各种实体类型的ID范围"""
    print(f"\n[5] 各实体类型的ID范围采样:")

    with open(entity_file, 'r') as f:
        data = json.load(f)

    if isinstance(data, dict):
        for entity_type, entity_list in data.items():
            if isinstance(entity_list, list) and len(entity_list) > 0:
                ids = []
                for entity in entity_list:
                    if 'id' in entity:
                        try:
                            ids.append(int(entity['id']))
                        except:
                            pass

                if ids:
                    ids.sort()
                    print(f"\n  {entity_type}:")
                    print(f"    数量: {len(ids)}")
                    print(f"    ID范围: {ids[0]} ~ {ids[-1]}")
                    print(f"    示例ID: {ids[:5]}")


def main():
    if len(sys.argv) > 1:
        target_id = sys.argv[1]
    else:
        target_id = "1548805"

    data_dir = Path("/data/xuao/code_kg_search/linux_test/data")
    entity_file = data_dir / "temp_en.json"
    relation_file = data_dir / "all_relation.json"

    # 1. 调试实体文件
    found = debug_entity_file(entity_file, target_id)

    # 2. 检查关系文件
    check_id_in_relations(relation_file, target_id)

    # 3. 采样实体类型
    sample_entity_types(entity_file)

    print("\n" + "="*80)
    print("调试完成")
    print("="*80)

    # 总结
    if not found:
        print("\n⚠️ 问题总结:")
        print(f"  - ID {target_id} 在关系中出现，但不在实体文件中")
        print(f"  - 可能原因:")
        print(f"    1. 实体数据不完整（某些实体类型缺失）")
        print(f"    2. ID {target_id} 是临时/中间节点，没有实体记录")
        print(f"    3. 数据生成时的Bug")


if __name__ == "__main__":
    main()
