#!/usr/bin/env python3
"""
分析FAIL_MESSAGE和FAIL_TEMPLATE的关联关系
尝试通过scope字段匹配函数实体
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

def build_function_index(entities):
    """建立函数名到ID的索引（支持同名函数）"""
    func_name_to_ids = defaultdict(list)
    func_by_id = {}

    for entity in entities:
        if entity.get('type') == 'FUNCTION':
            func_id = str(entity.get('id', ''))
            func_name = entity.get('name', '')
            if func_id and func_name:
                func_name_to_ids[func_name].append(func_id)
                func_by_id[func_id] = entity

    return func_name_to_ids, func_by_id

def analyze_fail_messages(entities, func_name_to_ids):
    """分析FAIL_MESSAGE实体"""
    fail_messages = [e for e in entities if e.get('type') == 'FAIL_MESSAGE']

    print(f"\n{'='*80}")
    print(f"分析FAIL_MESSAGE")
    print(f"{'='*80}")
    print(f"总数: {len(fail_messages):,}\n")

    # 统计scope字段
    scope_counts = defaultdict(int)
    matched_count = 0
    unmatched_count = 0

    for msg in fail_messages:
        scope = msg.get('scope', '')
        if scope:
            scope_counts[scope] += 1

            # 检查能否找到对应的函数
            if scope in func_name_to_ids:
                matched_count += 1
            else:
                unmatched_count += 1

    print(f"有scope字段的: {len([m for m in fail_messages if m.get('scope')])}")
    print(f"能匹配到函数的: {matched_count}")
    print(f"无法匹配的: {unmatched_count}\n")

    print(f"Top 20 scope值:")
    for scope, count in sorted(scope_counts.items(), key=lambda x: -x[1])[:20]:
        has_func = "✅" if scope in func_name_to_ids else "❌"
        print(f"  {has_func} {scope}: {count} 次")

    return fail_messages, scope_counts

def analyze_fail_templates(entities):
    """分析FAIL_TEMPLATE实体"""
    fail_templates = [e for e in entities if e.get('type') == 'FAIL_TEMPLATE']

    print(f"\n{'='*80}")
    print(f"分析FAIL_TEMPLATE")
    print(f"{'='*80}")
    print(f"总数: {len(fail_templates):,}\n")

    # 统计字段
    field_counts = defaultdict(int)
    for template in fail_templates:
        for key in template.keys():
            if key not in ['id', 'name', 'type']:
                field_counts[key] += 1

    if field_counts:
        print(f"其他字段统计:")
        for field, count in sorted(field_counts.items(), key=lambda x: -x[1]):
            print(f"  {field}: {count} 个实体有此字段")
    else:
        print("FAIL_TEMPLATE只有id, name, type三个字段")

    return fail_templates

def match_message_to_template(fail_messages, fail_templates):
    """尝试匹配FAIL_MESSAGE和FAIL_TEMPLATE"""
    print(f"\n{'='*80}")
    print(f"尝试匹配FAIL_MESSAGE和FAIL_TEMPLATE")
    print(f"{'='*80}\n")

    # 提取模板文本
    template_texts = {t.get('name', ''): t for t in fail_templates}

    # 尝试简单匹配（看name是否包含模板）
    matched_pairs = []

    for msg in fail_messages[:1000]:  # 先检查前1000个
        msg_name = msg.get('name', '')

        for template_text, template in template_texts.items():
            # 简单的包含检查（这可能不准确，但可以看趋势）
            if template_text and 'xxx' in template_text:
                # 去掉xxx，看是否能匹配
                template_pattern = template_text.replace('xxx', '').strip()
                if template_pattern and template_pattern in msg_name:
                    matched_pairs.append((msg, template))
                    break

    print(f"在前1000个FAIL_MESSAGE中，找到 {len(matched_pairs)} 个可能匹配的模板")

    if matched_pairs:
        print(f"\n匹配样本 (前5个):")
        for i, (msg, template) in enumerate(matched_pairs[:5], 1):
            print(f"\n[样本 {i}]")
            print(f"  FAIL_MESSAGE (ID={msg.get('id')})")
            print(f"    scope: {msg.get('scope', 'N/A')}")
            print(f"    line: {msg.get('start_line', 'N/A')}")
            print(f"    name: {msg.get('name', '')[:100]}...")
            print(f"  FAIL_TEMPLATE (ID={template.get('id')})")
            print(f"    name: {template.get('name', '')}")

def show_sample_details(fail_messages, func_name_to_ids, func_by_id):
    """展示几个FAIL_MESSAGE的详细匹配情况"""
    print(f"\n{'='*80}")
    print(f"FAIL_MESSAGE详细样本")
    print(f"{'='*80}\n")

    samples = fail_messages[:10]

    for i, msg in enumerate(samples, 1):
        print(f"[样本 {i}]")
        print(f"  FAIL_MESSAGE ID: {msg.get('id')}")
        print(f"  Name: {msg.get('name', '')[:80]}...")
        print(f"  Scope: {msg.get('scope', 'N/A')}")
        print(f"  Line: {msg.get('start_line', 'N/A')} - {msg.get('end_line', 'N/A')}")

        # 查找对应的函数
        scope = msg.get('scope', '')
        if scope in func_name_to_ids:
            func_ids = func_name_to_ids[scope]
            print(f"  ✅ 找到 {len(func_ids)} 个名为 '{scope}' 的函数:")
            for func_id in func_ids[:3]:  # 最多显示3个
                func = func_by_id.get(func_id, {})
                print(f"     - ID={func_id}, 文件: {func.get('source_file', 'N/A')}")
        else:
            print(f"  ❌ 未找到名为 '{scope}' 的函数")

        print()

def main():
    entity_file = "/data/xuao/code_kg_search/linux_test/data/temp_en.json"

    print("="*80)
    print("加载数据")
    print("="*80)
    entities = load_entities(entity_file)

    print("\n建立函数索引...")
    func_name_to_ids, func_by_id = build_function_index(entities)
    print(f"  函数数量: {len(func_by_id):,}")
    print(f"  唯一函数名: {len(func_name_to_ids):,}")

    # 分析FAIL_MESSAGE
    fail_messages, scope_counts = analyze_fail_messages(entities, func_name_to_ids)

    # 分析FAIL_TEMPLATE
    fail_templates = analyze_fail_templates(entities)

    # 尝试匹配
    match_message_to_template(fail_messages, fail_templates)

    # 展示详细样本
    show_sample_details(fail_messages, func_name_to_ids, func_by_id)

    print(f"\n{'='*80}")
    print(f"分析完成")
    print(f"{'='*80}")

    print(f"\n总结:")
    print(f"  - FAIL_MESSAGE虽然有scope字段，但没有关系边连接到函数")
    print(f"  - 需要通过scope字符串匹配函数名来建立关联")
    print(f"  - FAIL_TEMPLATE和FAIL_MESSAGE可能通过文本模式匹配关联")

if __name__ == "__main__":
    main()
