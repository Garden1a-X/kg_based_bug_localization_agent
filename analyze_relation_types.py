#!/usr/bin/env python3
"""
快速统计all_relation.json中的关系类型分布
"""
import json
import sys
from collections import defaultdict

def analyze_relation_types(relation_file):
    print("加载关系数据...")
    with open(relation_file, 'r', encoding='utf-8') as f:
        relations = json.load(f)

    print(f"总关系数: {len(relations):,}\n")

    # 统计关系类型
    type_counts = defaultdict(int)
    for rel in relations:
        rel_type = rel.get('type', 'UNKNOWN')
        type_counts[rel_type] += 1

    print("关系类型分布（按数量排序）:")
    print("=" * 60)
    for i, (rel_type, count) in enumerate(sorted(type_counts.items(), key=lambda x: x[1], reverse=True), 1):
        percentage = count / len(relations) * 100
        print(f"{i:2d}. {rel_type:<30} {count:>10,} ({percentage:>5.2f}%)")

    print("\n" + "=" * 60)

    # 特别检查ASSIGNED_TO
    if 'ASSIGNED_TO' in type_counts:
        print(f"\n✅ 找到ASSIGNED_TO关系: {type_counts['ASSIGNED_TO']:,} 条")

        # 显示前10个ASSIGNED_TO示例
        assigned_to_rels = [r for r in relations if r.get('type') == 'ASSIGNED_TO'][:10]
        print("\nASSIGNED_TO 示例:")
        for i, rel in enumerate(assigned_to_rels, 1):
            print(f"  [{i}] {rel}")
    else:
        print("\n❌ 未找到ASSIGNED_TO关系")

    # 检查DECL_IMPL
    if 'DECL_IMPL' in type_counts:
        print(f"\n✅ 找到DECL_IMPL关系: {type_counts['DECL_IMPL']:,} 条")
    else:
        print("\n❌ 未找到DECL_IMPL关系")

    # 检查类似的关系类型
    print("\n可能相关的关系类型:")
    keywords = ['DECL', 'IMPL', 'ASSIGN', 'POINT', 'CALLBACK', 'INDIRECT', 'ASYNC']
    for keyword in keywords:
        matching = [(name, count) for name, count in type_counts.items() if keyword.lower() in name.lower()]
        if matching:
            for name, count in matching:
                print(f"  - {name}: {count:,}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        relation_file = sys.argv[1]
    else:
        relation_file = "/data/xuao/code_kg_search/linux_test/data/all_relation.json"

    analyze_relation_types(relation_file)
