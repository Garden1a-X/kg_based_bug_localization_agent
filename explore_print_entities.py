#!/usr/bin/env python3
"""
探索图谱中print相关的实体和关系
重点关注type为FAIL_TEMPLATE、FAIL_MESSAGE等与bug报告相关的实体类型
"""

import json
from collections import defaultdict
from pathlib import Path

def load_entities(entity_file):
    """加载实体数据"""
    print(f"加载实体文件: {entity_file}")
    with open(entity_file, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    print(f"  实体总数: {len(entities):,}")
    return entities

def load_relations(relation_file):
    """加载关系数据"""
    print(f"加载关系文件: {relation_file}")
    with open(relation_file, 'r', encoding='utf-8') as f:
        relations = json.load(f)
    print(f"  关系总数: {len(relations):,}")
    return relations

def get_all_entity_types(entities):
    """获取所有实体类型"""
    type_counts = defaultdict(int)
    for entity in entities:
        entity_type = entity.get('type', 'UNKNOWN')
        type_counts[entity_type] += 1
    return type_counts

def filter_entities_by_type(entities, target_types):
    """根据type字段过滤实体"""
    results = defaultdict(list)

    for entity in entities:
        entity_type = entity.get('type', 'UNKNOWN')
        if entity_type in target_types:
            results[entity_type].append(entity)

    return results

def show_entity_samples(entity_type, entities, max_samples=10):
    """展示实体样本"""
    print(f"\n{'='*80}")
    print(f"实体类型: {entity_type}")
    print(f"数量: {len(entities)} 个")
    print(f"{'='*80}\n")

    print(f"样本 (前{min(max_samples, len(entities))}个):\n")

    for i, entity in enumerate(entities[:max_samples], 1):
        print(f"[样本 {i}]")
        print(f"  ID: {entity.get('id', 'N/A')}")
        print(f"  Name: {entity.get('name', 'N/A')}")
        print(f"  Type: {entity.get('type', 'N/A')}")

        # 显示所有其他字段
        for key, value in entity.items():
            if key not in ['id', 'name', 'type']:
                # 如果值太长，截断显示
                if isinstance(value, str) and len(value) > 200:
                    value = value[:200] + "..."
                print(f"  {key}: {value}")

        print()

def build_entity_index(entities):
    """建立实体ID索引"""
    entity_by_id = {}
    for entity in entities:
        entity_id = str(entity.get('id', ''))
        if entity_id:
            entity_by_id[entity_id] = entity
    return entity_by_id

def find_relations_for_entities(entity_ids, relations, max_show=30):
    """查找实体的相关关系"""
    print(f"\n{'='*80}")
    print(f"查找相关关系")
    print(f"{'='*80}\n")

    entity_id_set = set(entity_ids)
    related_relations = []
    relation_type_counts = defaultdict(int)

    for rel in relations:
        head = str(rel.get('head', ''))
        tail = str(rel.get('tail', ''))
        rel_type = rel.get('type', 'UNKNOWN')

        if head in entity_id_set or tail in entity_id_set:
            related_relations.append(rel)
            relation_type_counts[rel_type] += 1

    print(f"找到 {len(related_relations):,} 条相关关系\n")

    print(f"按关系类型统计:")
    for rel_type, count in sorted(relation_type_counts.items(), key=lambda x: -x[1]):
        print(f"  {rel_type}: {count:,} 条")

    return related_relations, relation_type_counts

def show_relation_details(relations, entity_by_id, max_show=20):
    """显示关系的详细信息（包含实体名称）"""
    print(f"\n关系详细信息 (前{max_show}条):")
    print(f"{'-'*80}\n")

    for i, rel in enumerate(relations[:max_show], 1):
        head_id = str(rel.get('head', ''))
        tail_id = str(rel.get('tail', ''))
        rel_type = rel.get('type', 'UNKNOWN')

        head_entity = entity_by_id.get(head_id, {})
        tail_entity = entity_by_id.get(tail_id, {})

        head_name = head_entity.get('name', f'ID:{head_id}')
        head_type = head_entity.get('type', 'UNKNOWN')
        tail_name = tail_entity.get('name', f'ID:{tail_id}')
        tail_type = tail_entity.get('type', 'UNKNOWN')

        print(f"[{i}] {head_name}({head_type}) --[{rel_type}]--> {tail_name}({tail_type})")

        # 如果有source_file信息，显示出来
        head_file = head_entity.get('source_file', '')
        tail_file = tail_entity.get('source_file', '')
        if head_file:
            print(f"    Head源文件: {head_file}")
        if tail_file and tail_file != head_file:
            print(f"    Tail源文件: {tail_file}")

        print()

def main():
    # 数据文件路径
    entity_file = "/data/xuao/code_kg_search/linux_test/data/temp_en.json"
    relation_file = "/data/xuao/code_kg_search/linux_test/data/all_relation.json"

    # 加载数据
    print("="*80)
    print("加载数据")
    print("="*80)
    entities = load_entities(entity_file)
    relations = load_relations(relation_file)

    # 建立实体索引
    print("\n建立实体ID索引...")
    entity_by_id = build_entity_index(entities)
    print(f"  索引完成: {len(entity_by_id):,} 个实体")

    # 先看看所有实体类型
    print(f"\n{'='*80}")
    print(f"统计所有实体类型")
    print(f"{'='*80}")
    type_counts = get_all_entity_types(entities)
    print(f"\n共有 {len(type_counts)} 种实体类型:\n")
    for entity_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {entity_type}: {count:,} 个")

    # 重点关注的类型
    target_types = ['FAIL_TEMPLATE', 'FAIL_MESSAGE', 'PRINT']

    print(f"\n{'='*80}")
    print(f"查找目标类型实体: {', '.join(target_types)}")
    print(f"{'='*80}")

    results = filter_entities_by_type(entities, target_types)

    # 对每个类型分析结果
    for entity_type in target_types:
        entities_found = results[entity_type]
        if not entities_found:
            print(f"\n类型 '{entity_type}': 未找到")
            continue

        # 展示样本
        show_entity_samples(entity_type, entities_found, max_samples=10)

        # 查找相关关系
        entity_ids = [str(e.get('id', '')) for e in entities_found]
        related_relations, rel_type_counts = find_relations_for_entities(entity_ids, relations)

        # 显示关系详细信息
        if related_relations:
            show_relation_details(related_relations[:20], entity_by_id, max_show=20)

    print(f"\n{'='*80}")
    print(f"分析完成")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
