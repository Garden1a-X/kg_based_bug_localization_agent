#!/usr/bin/env python3
"""
查看特定实体ID的详细信息
"""
import json
import sys
from pathlib import Path

def inspect_entity(entity_id, entity_file, relation_file):
    """检查特定实体的详细信息"""
    print(f"查找实体 ID: {entity_id}")
    print("="*80)

    # 加载实体
    print("\n加载实体数据...")
    with open(entity_file, 'r') as f:
        entities = json.load(f)

    # 查找实体
    target_entity = None
    if isinstance(entities, dict):
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                if str(entity.get('id')) == str(entity_id):
                    target_entity = entity
                    break
            if target_entity:
                break

    if not target_entity:
        print(f"❌ 未找到实体 ID: {entity_id}")
        return

    # 显示实体详情
    print(f"\n✅ 找到实体:")
    print(f"类型: {target_entity.get('type', 'UNKNOWN')}")
    print(f"名称: {target_entity.get('name', 'N/A')}")
    print(f"\n完整信息:")
    for key, value in target_entity.items():
        if key != 'code':  # code可能太长，单独处理
            print(f"  {key}: {value}")

    if 'code' in target_entity:
        code = target_entity['code']
        if len(code) > 200:
            print(f"  code: {code[:200]}... (长度: {len(code)})")
        else:
            print(f"  code: {code}")

    # 加载关系
    print(f"\n加载关系数据...")
    with open(relation_file, 'r') as f:
        relations = json.load(f)

    # 查找相关关系
    print(f"\n实体 {entity_id} 的相关关系:")

    # 作为head的关系
    head_rels = [r for r in relations if str(r.get('head')) == str(entity_id)]
    if head_rels:
        print(f"\n  作为源头 (head) 的关系: {len(head_rels)} 条")
        type_counts = {}
        for rel in head_rels:
            rel_type = rel.get('type')
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1

        for rel_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    - {rel_type}: {count} 条")

        # 显示前几个示例
        print(f"\n  示例 (前10条):")
        for i, rel in enumerate(head_rels[:10], 1):
            print(f"    [{i}] {rel.get('type')}: {entity_id} → {rel.get('tail')}")

    # 作为tail的关系
    tail_rels = [r for r in relations if str(r.get('tail')) == str(entity_id)]
    if tail_rels:
        print(f"\n  作为目标 (tail) 的关系: {len(tail_rels)} 条")
        type_counts = {}
        for rel in tail_rels:
            rel_type = rel.get('type')
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1

        for rel_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    - {rel_type}: {count} 条")

        # 显示前几个示例
        print(f"\n  示例 (前10条):")
        for i, rel in enumerate(tail_rels[:10], 1):
            print(f"    [{i}] {rel.get('type')}: {rel.get('head')} → {entity_id}")

    # 对于ASSIGNED_TO关系，查看目标实体
    if head_rels:
        assigned_to_rels = [r for r in head_rels if r.get('type') == 'ASSIGNED_TO']
        if assigned_to_rels:
            print(f"\n  ASSIGNED_TO 目标函数:")
            for rel in assigned_to_rels[:10]:
                tail_id = str(rel.get('tail'))
                # 查找目标实体
                for entity_type, entity_list in entities.items():
                    for entity in entity_list:
                        if str(entity.get('id')) == tail_id:
                            print(f"    → {entity.get('name', 'N/A')} (类型: {entity.get('type')}, ID: {tail_id})")
                            break

def main():
    if len(sys.argv) > 1:
        entity_ids = sys.argv[1:]
    else:
        # 默认查看trace_assigned_to.py发现的关键ID
        entity_ids = ['1548805']

    data_dir = Path("/data/xuao/code_kg_search/linux_test/data")
    entity_file = data_dir / "temp_en.json"
    relation_file = data_dir / "all_relation.json"

    for entity_id in entity_ids:
        inspect_entity(entity_id, entity_file, relation_file)
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
