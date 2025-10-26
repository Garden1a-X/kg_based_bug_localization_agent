#!/usr/bin/env python3
"""
诊断图谱数据 - 检查关键节点之间的关系和ID类型
"""
import json
import sys

# 支持命令行参数指定数据目录
if len(sys.argv) > 1:
    data_dir = sys.argv[1]
else:
    data_dir = "/data/xuao/code_kg_search/linux_test/data"

ENTITY_FILE = f"{data_dir}/temp_en.json"
RELATION_FILE = f"{data_dir}/relations.json"

print("=" * 80)
print("📊 图谱数据诊断 - ID类型检查")
print("=" * 80)
print(f"数据目录: {data_dir}")

# 加载数据
with open(ENTITY_FILE, 'r', encoding='utf-8') as f:
    entities = json.load(f)

with open(RELATION_FILE, 'r', encoding='utf-8') as f:
    relations = json.load(f)

print(f"\n总实体数: {len(entities)}")
print(f"总关系数: {len(relations)}")

# 构建ID到实体的映射，并检查ID类型
id_to_entity = {}
entity_id_types = set()
for entity in entities:
    if 'id' in entity:
        entity_id = entity['id']
        id_to_entity[entity_id] = entity
        entity_id_types.add(type(entity_id).__name__)

print(f"\n有ID的实体数: {len(id_to_entity)}")
print(f"实体ID类型: {entity_id_types}")

# 检查关系ID类型
relation_id_types = set()
sample_relation_ids = []
for i, rel in enumerate(relations[:10]):  # 取前10个作为样本
    if 'head' in rel:
        relation_id_types.add(type(rel['head']).__name__)
        if i < 3:
            sample_relation_ids.append(('head', rel['head'], type(rel['head']).__name__))
    if 'tail' in rel:
        relation_id_types.add(type(rel['tail']).__name__)
        if i < 3:
            sample_relation_ids.append(('tail', rel['tail'], type(rel['tail']).__name__))

print(f"\n关系ID类型: {relation_id_types}")
print(f"样本关系ID:")
for field, val, typ in sample_relation_ids[:5]:
    print(f"  {field}={val} (type: {typ})")

# **重要检查：类型不匹配警告**
if entity_id_types != relation_id_types:
    print(f"\n⚠️  警告：ID类型不匹配！")
    print(f"   实体ID类型: {entity_id_types}")
    print(f"   关系ID类型: {relation_id_types}")
    print(f"   这可能导致关系匹配失败！")

# 检查关键函数
key_functions = [
    "dw_mci_pltfm_probe",
    "dw_mci_pltfm_register",
    "dw_mci_probe",
    "mmc_start_host",
    "mmc_rescan",
    "mmc_execute_tuning",
    "dw_mci_execute_tuning"
]

print("\n" + "=" * 80)
print("🔍 检查关键函数")
print("=" * 80)

func_ids = {}
for func_name in key_functions:
    found = False
    for entity in entities:
        if entity.get('name') == func_name and entity.get('type') == 'FUNCTION':
            func_id = entity.get('id')
            is_decl = entity.get('is_declaration', False)
            func_ids[func_name] = func_id
            print(f"\n✓ {func_name}")
            print(f"   ID: {func_id} (类型: {type(func_id)})")
            print(f"   声明: {is_decl}")
            found = True
            break

    if not found:
        print(f"\n✗ {func_name} - 未找到")

# 特别检查 dw_mci_pltfm_register 的出边
print("\n" + "=" * 80)
print("🔬 特别检查: dw_mci_pltfm_register 的 CALLS 关系")
print("=" * 80)

target_func = "dw_mci_pltfm_register"
target_id = func_ids.get(target_func)

if target_id:
    print(f"\n函数: {target_func}")
    print(f"ID: {target_id} (type: {type(target_id).__name__})")

    # 检查有多少关系的 head 等于这个ID（考虑类型）
    exact_match_count = 0
    str_match_count = 0
    int_match_count = 0

    for rel in relations:
        rel_head = rel.get('head')
        rel_type = rel.get('type')

        # 精确匹配（类型和值都相同）
        if rel_head == target_id:
            exact_match_count += 1
            if exact_match_count <= 3:
                print(f"\n  ✓ 精确匹配 (type: {type(rel_head).__name__}):")
                print(f"    {rel_type}: head={rel_head} tail={rel.get('tail')}")

        # 字符串匹配
        if str(rel_head) == str(target_id):
            str_match_count += 1

        # 整数匹配（尝试转换）
        try:
            if int(rel_head) == int(target_id):
                int_match_count += 1
        except:
            pass

    print(f"\n匹配统计:")
    print(f"  精确匹配 (类型+值): {exact_match_count}")
    print(f"  字符串匹配 str(): {str_match_count}")
    print(f"  整数匹配 int(): {int_match_count}")

    if exact_match_count == 0 and str_match_count > 0:
        print(f"\n⚠️  发现问题：存在值相同但类型不同的匹配！")
        print(f"     实体ID类型: {type(target_id).__name__}")
        print(f"     需要检查关系中 head 的类型")
else:
    print(f"\n✗ 未找到函数: {target_func}")

# 统计关系类型
print("\n" + "=" * 80)
print("📋 关系类型统计")
print("=" * 80)

from collections import defaultdict
rel_types = defaultdict(int)

for rel in relations:
    rel_type = rel.get('type', 'UNKNOWN')
    rel_types[rel_type] += 1

for rel_type, count in sorted(rel_types.items(), key=lambda x: -x[1]):
    print(f"   {rel_type}: {count}")

# 检查关键节点对之间的关系
print("\n" + "=" * 80)
print("🔗 检查关键节点对的关系")
print("=" * 80)

# 我们想检查的节点对（根据预期路径）
check_pairs = [
    ("dw_mci_pltfm_probe", "dw_mci_pltfm_register"),
    ("dw_mci_pltfm_register", "dw_mci_probe"),
    ("dw_mci_probe", "mmc_start_host"),  # Mock: 函数指针
    ("mmc_start_host", "mmc_rescan"),    # Mock: 异步
    ("mmc_execute_tuning", "dw_mci_execute_tuning"),  # Mock: 函数指针
]

for from_func, to_func in check_pairs:
    print(f"\n{'─' * 80}")
    print(f"检查: {from_func} ➡️  {to_func}")

    from_id = func_ids.get(from_func)
    to_id = func_ids.get(to_func)

    if not from_id or not to_id:
        print(f"   ⚠️  节点ID不存在")
        continue

    print(f"   From ID: {from_id} ({type(from_id).__name__})")
    print(f"   To ID: {to_id} ({type(to_id).__name__})")

    # 查找所有类型的关系
    found_relations = []
    for rel in relations:
        head = rel.get('head')
        tail = rel.get('tail')
        rel_type = rel.get('type')

        # 检查所有可能的匹配（考虑类型转换）
        if (head == from_id and tail == to_id) or \
           (str(head) == str(from_id) and str(tail) == str(to_id)):
            found_relations.append(rel)

    if found_relations:
        print(f"   ✅ 找到 {len(found_relations)} 个关系:")
        for rel in found_relations:
            print(f"      - {rel.get('type')}: head={rel.get('head')} tail={rel.get('tail')}")
    else:
        print(f"   ❌ 未找到任何关系")

        # 查看从 from_id 出发的所有关系
        from_relations = []
        for rel in relations:
            if rel.get('head') == from_id or str(rel.get('head')) == str(from_id):
                from_relations.append(rel)

        if from_relations:
            print(f"   📍 从 {from_func} 出发的关系 ({len(from_relations)} 个):")
            for rel in from_relations[:5]:  # 只显示前5个
                tail = rel.get('tail')
                tail_entity = id_to_entity.get(tail)
                tail_name = tail_entity.get('name', 'Unknown') if tail_entity else 'Unknown'
                print(f"      - {rel.get('type')}: tail={tail} ({tail_name})")
            if len(from_relations) > 5:
                print(f"      ... 还有 {len(from_relations) - 5} 个")
        else:
            print(f"   ⚠️  从 {from_func} (ID:{from_id}) 没有任何出边！")

print("\n" + "=" * 80)
print("🔎 检查是否存在同名函数的多个实体")
print("=" * 80)

# 检查关键函数是否有多个实体
key_func_names_to_check = [
    "dw_mci_pltfm_register",
    "dw_mci_pltfm_probe",
    "dw_mci_probe",
]

for func_name in key_func_names_to_check:
    print(f"\n函数: {func_name}")
    matches = []
    for entity in entities:
        if entity.get('name') == func_name and entity.get('type') == 'FUNCTION':
            matches.append({
                'id': entity.get('id'),
                'is_decl': entity.get('is_declaration', False),
                'file': entity.get('file', 'N/A'),
                'start_line': entity.get('start_line', 'N/A'),
            })

    print(f"  找到 {len(matches)} 个实体:")
    for i, match in enumerate(matches, 1):
        print(f"    {i}. ID={match['id']}, 声明={match['is_decl']}, 文件={match['file']}, 行={match['start_line']}")

    # 如果有多个，检查哪个被 CALLS 关系使用
    if len(matches) > 1:
        print(f"\n  ⚠️  警告：存在 {len(matches)} 个同名实体！")
        print(f"  问题：self.entities['FUNCTION']['{func_name}'] 字典只能保留一个")
        print(f"  结果：find_function() 只会返回最后加载的那个，其他的会丢失！")

        print(f"\n  检查哪个ID被 CALLS 关系使用:")
        for match in matches:
            # 作为 tail（被调用）
            as_tail = sum(1 for rel in relations if rel.get('type') == 'CALLS' and rel.get('tail') == match['id'])
            # 作为 head（调用者）
            as_head = sum(1 for rel in relations if rel.get('type') == 'CALLS' and rel.get('head') == match['id'])
            usage = "✓ 活跃" if (as_head > 0 or as_tail > 0) else "✗ 未使用"
            print(f"    ID {match['id']}: 作为调用者 {as_head} 次, 作为被调用者 {as_tail} 次 [{usage}]")

print("\n" + "=" * 80)
print("🧪 模拟 kg_interface.py 的加载逻辑")
print("=" * 80)

print("\n模拟：按照 kg_interface 的方式加载实体到字典...")
simulated_entities = {}
for entity in entities:
    if entity.get('type') == 'FUNCTION':
        func_name = entity.get('name')
        if func_name in key_func_names_to_check:
            # 模拟加载逻辑（后加载的会覆盖先加载的）
            old_id = simulated_entities.get(func_name, {}).get('id')
            new_id = entity.get('id')
            if old_id and old_id != new_id:
                print(f"\n⚠️  {func_name}: ID {old_id} 被 ID {new_id} 覆盖！")
            simulated_entities[func_name] = entity

print("\n最终 find_function() 会返回的ID:")
for func_name in key_func_names_to_check:
    if func_name in simulated_entities:
        final_id = simulated_entities[func_name]['id']
        print(f"  {func_name}: ID={final_id}")

        # 检查这个ID是否有 CALLS 关系
        as_head = sum(1 for rel in relations if rel.get('type') == 'CALLS' and rel.get('head') == final_id)
        as_tail = sum(1 for rel in relations if rel.get('type') == 'CALLS' and rel.get('tail') == final_id)

        if as_head == 0 and as_tail == 0:
            print(f"    ❌ 这个ID在 CALLS 关系中完全未使用！")
        else:
            print(f"    ✓ 调用者 {as_head} 次, 被调用者 {as_tail} 次")

print("\n" + "=" * 80)
print("💡 建议的修复方案")
print("=" * 80)

# 检查是否有同名函数问题
has_duplicate_functions = False
for func_name in key_func_names_to_check:
    count = sum(1 for e in entities if e.get('name') == func_name and e.get('type') == 'FUNCTION')
    if count > 1:
        has_duplicate_functions = True
        break

if has_duplicate_functions:
    print("\n❌ 发现核心问题：同名函数导致ID冲突！")
    print("\n问题根源：")
    print("  1. 图谱中存在多个同名函数实体（可能来自不同文件或声明/实现）")
    print("  2. kg_interface.py 使用字典存储：self.entities['FUNCTION'][name] = entity")
    print("  3. 后加载的实体会覆盖先加载的，导致 find_function() 返回错误的ID")
    print("  4. CALLS 关系指向被覆盖的旧ID，所以查询时找不到关系")
    print("\n推荐方案：")
    print("  方案A: 使用 entity_by_id 查找（推荐）")
    print("    - 在 get_callees/get_callers 中直接使用 entity_by_id[id]")
    print("    - 避免通过 find_function(name) 间接查找")
    print("    - 确保使用关系中实际存在的ID")
    print("\n  方案B: 改进实体存储结构")
    print("    - 将 self.entities['FUNCTION'] 从 {name: entity} 改为 {name: [entities]}")
    print("    - find_function 返回所有同名实体，让调用者选择")
    print("    - 需要大量代码改动")
    print("\n  方案C: 过滤掉未使用的实体")
    print("    - 在加载时，只保留在 CALLS 关系中使用的实体")
    print("    - 需要先加载关系，再过滤实体")
    print("\n  建议：先用方案A快速修复，后续考虑方案B优化架构")
elif entity_id_types != relation_id_types:
    print("\n检测到ID类型不匹配，建议在代码中统一ID类型:")
    print("\n方案1: 在加载数据时统一转换为字符串")
    print("  - 修改 kg_interface.py 的 _load_merged_format 方法")
    print("  - 在加载实体和关系时，将所有ID转换为 str()")
    print("\n方案2: 在比较时进行类型转换")
    print("  - 修改 get_callees/get_callers 方法")
    print("  - 在检查 'head in equivalent_ids' 时，统一类型")
    print("\n推荐：方案1（更彻底，避免后续问题）")
elif exact_match_count > 0:
    print("\n✓ ID类型匹配正常，关系存在")
    print("  如果仍然搜索失败，检查其他逻辑（如等价ID映射）")
else:
    print("\n✓ ID类型匹配正常")
    print(f"  但 {target_func} 确实没有 CALLS 关系")
    print("  检查图谱数据是否完整")

print("\n" + "=" * 80)
print("✅ 诊断完成")
print("=" * 80)
