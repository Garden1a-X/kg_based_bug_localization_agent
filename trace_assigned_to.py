#!/usr/bin/env python3
"""
追踪特定函数对之间的ASSIGNED_TO关系（可能通过中间节点）
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

def load_data(entity_file, relation_file):
    """加载实体和关系数据"""
    print("加载数据...")

    with open(entity_file, 'r') as f:
        entities = json.load(f)

    with open(relation_file, 'r') as f:
        relations = json.load(f)

    return entities, relations

def build_indexes(entities, relations):
    """建立索引"""
    print("建立索引...")

    # 函数索引
    function_by_name = {}
    entity_by_id = {}

    if isinstance(entities, dict):
        functions = entities.get('FUNCTION', entities.get('Function', []))
    else:
        functions = [e for e in entities if e.get('type') == 'FUNCTION']

    for func in functions:
        name = func.get('name')
        func_id = str(func.get('id'))
        if name:
            if name not in function_by_name:
                function_by_name[name] = []
            function_by_name[name].append(func)
        entity_by_id[func_id] = func

    # 所有实体索引
    if isinstance(entities, dict):
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                entity_id = str(entity.get('id'))
                entity_by_id[entity_id] = entity

    # ASSIGNED_TO关系索引
    assigned_to_rels = [r for r in relations if r.get('type') == 'ASSIGNED_TO']

    # 从某个实体出发的ASSIGNED_TO
    assigned_from = defaultdict(list)
    # 到达某个实体的ASSIGNED_TO
    assigned_to = defaultdict(list)

    for rel in assigned_to_rels:
        head = str(rel.get('head'))
        tail = str(rel.get('tail'))
        assigned_from[head].append((tail, rel))
        assigned_to[tail].append((head, rel))

    print(f"函数数量: {len(function_by_name)}")
    print(f"实体总数: {len(entity_by_id)}")
    print(f"ASSIGNED_TO关系: {len(assigned_to_rels):,}")

    return function_by_name, entity_by_id, assigned_from, assigned_to

def trace_assigned_to_path(func_a, func_b, function_by_name, entity_by_id, assigned_from, assigned_to):
    """追踪两个函数之间的ASSIGNED_TO路径"""
    print(f"\n{'='*80}")
    print(f"追踪: {func_a} → {func_b}")
    print(f"{'='*80}")

    # 获取函数ID
    func_a_entities = function_by_name.get(func_a, [])
    func_b_entities = function_by_name.get(func_b, [])

    if not func_a_entities:
        print(f"❌ 函数 {func_a} 不存在")
        return
    if not func_b_entities:
        print(f"❌ 函数 {func_b} 不存在")
        return

    func_a_ids = [str(e.get('id')) for e in func_a_entities]
    func_b_ids = [str(e.get('id')) for e in func_b_entities]

    print(f"\n函数A ({func_a}): {len(func_a_ids)} 个ID")
    for fid in func_a_ids:
        print(f"  - {fid}")

    print(f"\n函数B ({func_b}): {len(func_b_ids)} 个ID")
    for fid in func_b_ids:
        print(f"  - {fid}")

    # 1. 检查直接ASSIGNED_TO关系
    print(f"\n[1] 检查直接ASSIGNED_TO (A → B):")
    found_direct = False
    for a_id in func_a_ids:
        for b_id, rel in assigned_from.get(a_id, []):
            if b_id in func_b_ids:
                print(f"  ✅ 找到: {a_id} → {b_id}")
                print(f"     {rel}")
                found_direct = True

    if not found_direct:
        print(f"  ❌ 未找到直接ASSIGNED_TO关系")

    # 2. 检查A的所有ASSIGNED_TO目标（可能是中间节点）
    print(f"\n[2] 检查A的所有ASSIGNED_TO目标:")
    a_targets = set()
    for a_id in func_a_ids:
        targets = assigned_from.get(a_id, [])
        if targets:
            print(f"  函数A (ID {a_id}) ASSIGNED_TO:")
            for target_id, rel in targets[:10]:  # 只显示前10个
                target_entity = entity_by_id.get(target_id, {})
                target_type = target_entity.get('type', 'UNKNOWN')
                target_name = target_entity.get('name', f'ID:{target_id}')
                print(f"    → {target_name} (类型: {target_type}, ID: {target_id})")
                a_targets.add(target_id)
            if len(targets) > 10:
                print(f"    ... 还有 {len(targets)-10} 个")

    # 3. 检查B的所有ASSIGNED_TO来源
    print(f"\n[3] 检查B的所有ASSIGNED_TO来源:")
    b_sources = set()
    for b_id in func_b_ids:
        sources = assigned_to.get(b_id, [])
        if sources:
            print(f"  函数B (ID {b_id}) 被ASSIGNED_TO:")
            for source_id, rel in sources[:10]:
                source_entity = entity_by_id.get(source_id, {})
                source_type = source_entity.get('type', 'UNKNOWN')
                source_name = source_entity.get('name', f'ID:{source_id}')
                print(f"    ← {source_name} (类型: {source_type}, ID: {source_id})")
                b_sources.add(source_id)
            if len(sources) > 10:
                print(f"    ... 还有 {len(sources)-10} 个")

    # 4. 检查是否有共同的中间节点
    print(f"\n[4] 检查共同的中间节点:")
    common = a_targets & b_sources
    if common:
        print(f"  ✅ 找到 {len(common)} 个共同中间节点:")
        for mid_id in list(common)[:10]:
            mid_entity = entity_by_id.get(mid_id, {})
            mid_type = mid_entity.get('type', 'UNKNOWN')
            mid_name = mid_entity.get('name', f'ID:{mid_id}')
            print(f"    - {mid_name} (类型: {mid_type})")
            print(f"      路径: {func_a} → {mid_name} → {func_b}")
    else:
        print(f"  ❌ 未找到共同中间节点")

    # 5. 2跳搜索：A → X → B
    print(f"\n[5] 2跳搜索 (A → X → B):")
    paths_found = []
    for a_id in func_a_ids:
        for mid_id, _ in assigned_from.get(a_id, []):
            for target_id, _ in assigned_from.get(mid_id, []):
                if target_id in func_b_ids:
                    mid_entity = entity_by_id.get(mid_id, {})
                    mid_name = mid_entity.get('name', f'ID:{mid_id}')
                    mid_type = mid_entity.get('type', 'UNKNOWN')
                    paths_found.append((a_id, mid_id, mid_name, mid_type, target_id))

    if paths_found:
        print(f"  ✅ 找到 {len(paths_found)} 条2跳路径:")
        for a_id, mid_id, mid_name, mid_type, b_id in paths_found[:5]:
            print(f"    {func_a}(ID:{a_id}) → {mid_name}({mid_type}, ID:{mid_id}) → {func_b}(ID:{b_id})")
        if len(paths_found) > 5:
            print(f"    ... 还有 {len(paths_found)-5} 条")
    else:
        print(f"  ❌ 未找到2跳路径")

def main():
    if len(sys.argv) > 2:
        entity_file = sys.argv[1]
        relation_file = sys.argv[2]
    else:
        data_dir = Path("/data/xuao/code_kg_search/linux_test/data")
        entity_file = data_dir / "temp_en.json"
        relation_file = data_dir / "all_relation.json"

    # 加载数据
    entities, relations = load_data(entity_file, relation_file)

    # 建立索引
    function_by_name, entity_by_id, assigned_from, assigned_to = build_indexes(entities, relations)

    # 追踪4个不可达节点对
    pairs = [
        ("dw_mci_init_slot", "mmc_add_host"),
        ("mmc_schedule_delayed_work", "mmc_rescan"),
        ("mmc_execute_tuning", "dw_mci_execute_tuning"),
        ("dw_mci_execute_tuning", "dw_mci_hi3660_execute_tuning"),
    ]

    for func_a, func_b in pairs:
        trace_assigned_to_path(func_a, func_b, function_by_name, entity_by_id, assigned_from, assigned_to)

    print("\n" + "="*80)
    print("追踪完成")
    print("="*80)

if __name__ == "__main__":
    main()
