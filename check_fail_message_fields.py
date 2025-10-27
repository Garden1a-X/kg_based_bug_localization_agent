#!/usr/bin/env python3
"""
检查FAIL_MESSAGE实体的所有字段
看是否有source_file或其他定位信息
"""

import json
from collections import defaultdict

def load_entities(entity_file):
    """加载实体数据"""
    print(f"加载实体文件: {entity_file}")
    with open(entity_file, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    print(f"  实体总数: {len(entities):,}")
    return entities

def analyze_fail_message_fields(entities):
    """分析FAIL_MESSAGE的所有字段"""
    fail_messages = [e for e in entities if e.get('type') == 'FAIL_MESSAGE']

    print(f"\n{'='*80}")
    print(f"分析FAIL_MESSAGE字段")
    print(f"{'='*80}")
    print(f"总数: {len(fail_messages):,}\n")

    # 统计所有字段
    field_counts = defaultdict(int)
    field_values = defaultdict(set)

    for msg in fail_messages:
        for key, value in msg.items():
            field_counts[key] += 1
            # 对于非字符串或短字符串，记录值
            if not isinstance(value, str) or len(str(value)) < 50:
                field_values[key].add(str(value))

    print("字段统计:")
    for field in sorted(field_counts.keys()):
        count = field_counts[field]
        percentage = count / len(fail_messages) * 100
        print(f"  {field}: {count:,} ({percentage:.1f}%)")

        # 如果值的种类很少，显示出来
        if field not in ['id', 'name', 'type'] and len(field_values[field]) <= 20:
            values = sorted(field_values[field])
            print(f"    值: {values}")

    # 展示完整样本
    print(f"\n{'='*80}")
    print(f"完整样本 (前10个)")
    print(f"{'='*80}\n")

    for i, msg in enumerate(fail_messages[:10], 1):
        print(f"[样本 {i}]")
        for key in sorted(msg.keys()):
            value = msg[key]
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            print(f"  {key}: {value}")
        print()

def main():
    entity_file = "/data/xuao/code_kg_search/linux_test/data/temp_en.json"

    print("="*80)
    print("检查FAIL_MESSAGE字段")
    print("="*80)
    entities = load_entities(entity_file)

    analyze_fail_message_fields(entities)

    print(f"\n{'='*80}")
    print(f"检查完成")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
