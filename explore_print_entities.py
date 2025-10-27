#!/usr/bin/env python3
"""
探索图谱中print相关的实体和关系
重点关注FAIL_TEMPLATE、FAIL_MESSAGE等与bug报告相关的内容
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

def search_entities_by_keywords(entities, keywords):
    """根据关键词搜索实体"""
    results = defaultdict(list)

    for entity in entities:
        entity_name = entity.get('name', '').lower()
        entity_type = entity.get('type', 'UNKNOWN')

        for keyword in keywords:
            if keyword.lower() in entity_name:
                results[keyword].append(entity)

    return results

def analyze_entity_group(keyword, entities):
    """分析一组实体"""
    print(f"\n{'='*80}")
    print(f"关键词: {keyword}")
    print(f"{'='*80}")
    print(f"找到 {len(entities)} 个实体\n")

    # 按类型分组统计
    type_counts = defaultdict(int)
    for entity in entities:
        entity_type = entity.get('type', 'UNKNOWN')
        type_counts[entity_type] += 1

    print(f"按类型统计:")
    for entity_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {entity_type}: {count} 个")

    return type_counts

def show_entity_samples(keyword, entities, max_samples=10):
    """展示实体样本"""
    print(f"\n{'='*80}")
    print(f"'{keyword}' 实体样本 (前{max_samples}个)")
    print(f"{'='*80}\n")

    for i, entity in enumerate(entities[:max_samples], 1):
        print(f"[样本 {i}]")
        print(f"  ID: {entity.get('id', 'N/A')}")
        print(f"  Name: {entity.get('name', 'N/A')}")
        print(f"  Type: {entity.get('type', 'N/A')}")

        # 显示其他有用的字段
        for key in ['style', 'scope', 'source_file', 'definition', 'value']:
            if key in entity and entity[key]:
                value = entity[key]
                # 如果值太长，截断显示
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                print(f"  {key}: {value}")

        print()

def find_relations_for_entities(entity_ids, relations, max_relations=20):
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
    for rel_type, count in sorted(relation_type_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {rel_type}: {count:,} 条")

    # 展示一些关系样本
    if related_relations:
        print(f"\n关系样本 (前{max_relations}条):")
        for i, rel in enumerate(related_relations[:max_relations], 1):
            print(f"  [{i}] {rel.get('head', 'N/A')} --[{rel.get('type', 'N/A')}]--> {rel.get('tail', 'N/A')}")

    return related_relations, relation_type_counts

def build_entity_index(entities):
    """建立实体ID索引"""
    entity_by_id = {}
    for entity in entities:
        entity_id = str(entity.get('id', ''))
        if entity_id:
            entity_by_id[entity_id] = entity
    return entity_by_id

def show_relation_details(relations, entity_by_id, max_show=10):
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
        if 'source_file' in head_entity:
            print(f"    源文件: {head_entity['source_file']}")
        if 'source_file' in tail_entity and tail_entity.get('source_file') != head_entity.get('source_file'):
            print(f"    目标文件: {tail_entity['source_file']}")

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

    # 搜索关键词
    keywords = [
        'print',
        'FAIL_TEMPLATE',
        'FAIL_MESSAGE',
        'dev_err',
        'dev_warn',
        'pr_err',
        'pr_warn',
        'pr_info',
    ]

    print(f"\n{'='*80}")
    print(f"搜索关键词: {', '.join(keywords)}")
    print(f"{'='*80}")

    results = search_entities_by_keywords(entities, keywords)

    # 对每个关键词分析结果
    for keyword in keywords:
        entities_found = results[keyword]
        if not entities_found:
            print(f"\n关键词 '{keyword}': 未找到相关实体")
            continue

        # 分析实体类型分布
        analyze_entity_group(keyword, entities_found)

        # 展示样本
        show_entity_samples(keyword, entities_found, max_samples=5)

        # 查找相关关系
        entity_ids = [str(e.get('id', '')) for e in entities_found[:50]]  # 取前50个实体查找关系
        related_relations, rel_type_counts = find_relations_for_entities(entity_ids, relations, max_relations=20)

        # 显示关系详细信息
        if related_relations:
            show_relation_details(related_relations[:10], entity_by_id, max_show=10)

    print(f"\n{'='*80}")
    print(f"分析完成")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
