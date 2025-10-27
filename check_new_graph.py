#!/usr/bin/env python3
"""
检查新图谱（all_relation.json）的格式和16节点路径连通性
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

def check_new_graph_format(graph_file):
    """检查新图谱的格式"""
    print("=" * 80)
    print("检查新图谱格式")
    print("=" * 80)

    print(f"\n文件: {graph_file}")

    # 检查文件大小
    file_size = Path(graph_file).stat().st_size
    print(f"文件大小: {file_size / 1024 / 1024:.2f} MB")

    # 加载数据
    print("\n加载数据...")
    with open(graph_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 分析数据结构
    print(f"\n数据类型: {type(data)}")

    if isinstance(data, dict):
        print(f"顶层键: {list(data.keys())}")

        # 显示每个键的数据量
        for key, value in data.items():
            if isinstance(value, list):
                print(f"  {key}: {len(value)} 条记录")
                if len(value) > 0:
                    print(f"    示例: {value[0]}")
            elif isinstance(value, dict):
                print(f"  {key}: {len(value)} 个子项")
            else:
                print(f"  {key}: {type(value)}")

    elif isinstance(data, list):
        print(f"数据长度: {len(data)}")
        if len(data) > 0:
            print(f"第一条记录: {data[0]}")
            print(f"第一条记录的键: {list(data[0].keys()) if isinstance(data[0], dict) else 'N/A'}")

    return data


def build_function_index(data):
    """从数据中建立函数索引"""
    print("\n" + "=" * 80)
    print("建立函数索引")
    print("=" * 80)

    function_by_name = {}
    function_by_id = {}

    # 尝试不同的数据结构
    if isinstance(data, dict):
        # 格式1: {entity_type: [entities]}
        if 'FUNCTION' in data or 'Function' in data:
            functions = data.get('FUNCTION', data.get('Function', []))
            print(f"\n找到 {len(functions)} 个函数（格式1）")

            for func in functions:
                name = func.get('name')
                func_id = func.get('id')
                if name:
                    if name not in function_by_name:
                        function_by_name[name] = []
                    function_by_name[name].append(func)
                if func_id:
                    function_by_id[str(func_id)] = func

        # 格式2: 可能是关系数据
        elif 'CALLS' in data or 'calls' in data:
            print("\n这似乎是关系文件，不是实体文件")
            print(f"关系类型: {list(data.keys())}")

    elif isinstance(data, list):
        # 格式3: [entities]
        functions = [item for item in data if item.get('type') == 'FUNCTION']
        print(f"\n找到 {len(functions)} 个函数（格式3）")

        for func in functions:
            name = func.get('name')
            func_id = func.get('id')
            if name:
                if name not in function_by_name:
                    function_by_name[name] = []
                function_by_name[name].append(func)
            if func_id:
                function_by_id[str(func_id)] = func

    print(f"\n索引统计:")
    print(f"  按名称索引: {len(function_by_name)} 个唯一函数名")
    print(f"  按ID索引: {len(function_by_id)} 个函数ID")

    # 显示同名函数
    multi_id_funcs = {name: ids for name, ids in function_by_name.items() if len(ids) > 1}
    if multi_id_funcs:
        print(f"\n  有多个ID的函数: {len(multi_id_funcs)} 个")
        for name, funcs in list(multi_id_funcs.items())[:5]:
            print(f"    {name}: {len(funcs)} 个ID")

    return function_by_name, function_by_id


def build_call_graph(data, function_by_id):
    """从数据中建立调用图"""
    print("\n" + "=" * 80)
    print("建立调用图")
    print("=" * 80)

    call_graph = defaultdict(set)  # {caller_name: {callee_names}}

    if isinstance(data, dict):
        # 查找CALLS关系
        calls = data.get('CALLS', data.get('calls', []))
        print(f"\n找到 {len(calls)} 条CALLS关系")

        for rel in calls[:10]:  # 显示前10条
            print(f"  示例: {rel}")

        # 构建调用图
        for rel in calls:
            head = str(rel.get('head', rel.get('source', '')))
            tail = str(rel.get('tail', rel.get('target', '')))

            if head in function_by_id and tail in function_by_id:
                caller_name = function_by_id[head].get('name')
                callee_name = function_by_id[tail].get('name')
                if caller_name and callee_name:
                    call_graph[caller_name].add(callee_name)

    print(f"\n调用图统计:")
    print(f"  调用者数量: {len(call_graph)}")
    print(f"  总调用边数: {sum(len(callees) for callees in call_graph.values())}")

    return dict(call_graph)


def check_16_node_path(function_by_name, call_graph, all_relations, function_by_id):
    """检查16节点路径的连通性"""
    print("\n" + "=" * 80)
    print("检查16节点路径连通性")
    print("=" * 80)

    # 16节点路径
    expected_path = [
        "dw_mci_pltfm_probe",
        "dw_mci_pltfm_register",
        "dw_mci_probe",
        "dw_mci_init_slot",
        "mmc_add_host",
        "mmc_start_host",
        "_mmc_detect_change",
        "mmc_schedule_delayed_work",
        "mmc_rescan",
        "mmc_rescan_try_freq",
        "mmc_attach_mmc",
        "mmc_init_card",
        "mmc_hs200_tuning",
        "mmc_execute_tuning",
        "dw_mci_execute_tuning",
        "dw_mci_hi3660_execute_tuning"
    ]

    # 检查节点存在性
    print("\n[1/2] 检查节点是否存在:")
    missing_nodes = []
    for i, node in enumerate(expected_path, 1):
        if node in function_by_name:
            num_ids = len(function_by_name[node])
            print(f"  ✅ [{i:2d}] {node:<40} ({num_ids} 个ID)")
        else:
            print(f"  ❌ [{i:2d}] {node:<40} (不存在)")
            missing_nodes.append(node)

    if missing_nodes:
        print(f"\n⚠️  缺失节点: {len(missing_nodes)} 个")
        return
    else:
        print(f"\n✅ 所有16个节点都存在!")

    # 检查边的连通性
    print("\n[2/2] 检查相邻节点的连通性:")

    reachable = 0
    unreachable = 0
    unreachable_pairs = []

    for i in range(len(expected_path) - 1):
        caller = expected_path[i]
        callee = expected_path[i + 1]

        # 检查是否有直接调用关系
        is_connected = caller in call_graph and callee in call_graph[caller]

        if is_connected:
            reachable += 1
            print(f"  ✅ [{i+1:2d}→{i+2:2d}] {caller:<40} → {callee}")
        else:
            unreachable += 1
            unreachable_pairs.append((i+1, caller, callee))
            print(f"  ❌ [{i+1:2d}→{i+2:2d}] {caller:<40} → {callee}")

    # 统计
    print(f"\n连通性统计:")
    print(f"  ✅ 可达: {reachable}/{len(expected_path)-1}")
    print(f"  ❌ 不可达: {unreachable}/{len(expected_path)-1}")

    if unreachable_pairs:
        print(f"\n❌ 不可达的节点对（需要间接调用或Mock）:")
        for pos, caller, callee in unreachable_pairs:
            print(f"  [{pos:2d}→{pos+1:2d}] {caller} → {callee}")

        # 检查这些节点对之间是否有其他类型的关系
        print(f"\n🔍 检查不可达节点对的其他关系类型:")
        # 需要先建立DECL_IMPL映射
        decl_to_impl, impl_to_decl = build_decl_impl_mapping(all_relations)
        check_alternative_relations(unreachable_pairs, function_by_name, all_relations, function_by_id, decl_to_impl, impl_to_decl)

    return reachable, unreachable


def build_decl_impl_mapping(relations):
    """建立声明-实现映射"""
    print("\n" + "=" * 80)
    print("建立声明-实现映射")
    print("=" * 80)

    decl_to_impl = {}
    impl_to_decl = {}

    decl_impl_rels = [r for r in relations if r.get('type') == 'DECL_IMPL']
    print(f"\n找到 {len(decl_impl_rels)} 条DECL_IMPL关系")

    for rel in decl_impl_rels:
        decl_id = str(rel.get('head', ''))
        impl_id = str(rel.get('tail', ''))
        if decl_id and impl_id:
            decl_to_impl[decl_id] = impl_id
            impl_to_decl[impl_id] = decl_id

    print(f"声明→实现映射: {len(decl_to_impl)} 条")
    print(f"实现→声明映射: {len(impl_to_decl)} 条")

    return decl_to_impl, impl_to_decl


def get_all_equivalent_ids(func_id, decl_to_impl, impl_to_decl):
    """获取函数ID的所有等价ID（包括声明和实现）"""
    equivalent_ids = {func_id}

    # 如果是声明，添加实现
    if func_id in decl_to_impl:
        equivalent_ids.add(decl_to_impl[func_id])

    # 如果是实现，添加声明
    if func_id in impl_to_decl:
        equivalent_ids.add(impl_to_decl[func_id])

    return equivalent_ids


def check_alternative_relations(unreachable_pairs, function_by_name, all_relations, function_by_id, decl_to_impl, impl_to_decl):
    """检查不可达节点对之间的其他关系类型"""

    # 构建ID到名称的反向映射
    id_to_name = {func_id: func.get('name') for func_id, func in function_by_id.items()}

    for pos, caller_name, callee_name in unreachable_pairs:
        print(f"\n  [{pos:2d}→{pos+1:2d}] {caller_name} → {callee_name}:")

        # 获取caller和callee的所有ID（包括声明和实现）
        caller_base_ids = [str(func.get('id')) for func in function_by_name.get(caller_name, [])]
        callee_base_ids = [str(func.get('id')) for func in function_by_name.get(callee_name, [])]

        if not caller_base_ids or not callee_base_ids:
            print(f"    ⚠️  无法获取函数ID")
            continue

        # 扩展到所有等价ID
        caller_ids = set()
        for base_id in caller_base_ids:
            caller_ids.update(get_all_equivalent_ids(base_id, decl_to_impl, impl_to_decl))

        callee_ids = set()
        for base_id in callee_base_ids:
            callee_ids.update(get_all_equivalent_ids(base_id, decl_to_impl, impl_to_decl))

        print(f"    调试: caller有 {len(caller_base_ids)} 个基础ID, 扩展到 {len(caller_ids)} 个等价ID")
        print(f"    调试: callee有 {len(callee_base_ids)} 个基础ID, 扩展到 {len(callee_ids)} 个等价ID")
        print(f"    调试: caller IDs: {caller_ids}")
        print(f"    调试: callee IDs: {callee_ids}")

        # 查找这些ID之间的所有关系
        relations_found = defaultdict(list)

        for rel in all_relations:
            head = str(rel.get('head', ''))
            tail = str(rel.get('tail', ''))
            rel_type = rel.get('type', 'UNKNOWN')

            # 检查是否是caller到callee的关系（任意方向）
            if head in caller_ids and tail in callee_ids:
                relations_found[rel_type].append(rel)
            elif head in callee_ids and tail in caller_ids:
                # 反向关系也记录
                relations_found[f'{rel_type}_REVERSE'].append(rel)

        if relations_found:
            print(f"    ✅ 找到其他关系:")
            for rel_type, rels in relations_found.items():
                print(f"      - {rel_type}: {len(rels)} 条")
                # 显示前3个示例
                for i, rel in enumerate(rels[:3]):
                    head_name = id_to_name.get(str(rel.get('head')), f"ID:{rel.get('head')}")
                    tail_name = id_to_name.get(str(rel.get('tail')), f"ID:{rel.get('tail')}")
                    print(f"        [{i+1}] {head_name} → {tail_name}")
                    print(f"            {rel}")
        else:
            print(f"    ❌ 未找到任何关系（检查了 {len(caller_ids)} × {len(callee_ids)} = {len(caller_ids)*len(callee_ids)} 种ID组合）")


def check_relation_types(data):
    """检查图谱中有哪些关系类型"""
    print("\n" + "=" * 80)
    print("检查关系类型")
    print("=" * 80)

    if isinstance(data, dict):
        print("\n关系类型:")
        for key, value in data.items():
            if isinstance(value, list):
                print(f"  {key}: {len(value)} 条")
                if len(value) > 0 and isinstance(value[0], dict):
                    print(f"    字段: {list(value[0].keys())}")

    # 特别检查PRINT/LOG关系
    print("\n检查日志相关关系:")
    has_print = False
    for key in ['PRINT', 'print', 'LOG', 'log', 'PRINTF', 'printf']:
        if key in data:
            print(f"  ✅ 找到 {key} 关系: {len(data[key])} 条")
            has_print = True
            if len(data[key]) > 0:
                print(f"    示例: {data[key][0]}")

    if not has_print:
        print(f"  ⚠️  未找到PRINT/LOG相关关系")


def load_entities(entity_file):
    """加载实体文件"""
    print("=" * 80)
    print("加载实体文件")
    print("=" * 80)

    print(f"\n文件: {entity_file}")
    file_size = Path(entity_file).stat().st_size
    print(f"文件大小: {file_size / 1024 / 1024:.2f} MB")

    print("\n加载数据...")
    with open(entity_file, 'r', encoding='utf-8') as f:
        entities = json.load(f)

    return entities


def load_relations(relation_file):
    """加载关系文件"""
    print("\n" + "=" * 80)
    print("加载关系文件")
    print("=" * 80)

    print(f"\n文件: {relation_file}")
    file_size = Path(relation_file).stat().st_size
    print(f"文件大小: {file_size / 1024 / 1024:.2f} MB")

    print("\n加载数据...")
    with open(relation_file, 'r', encoding='utf-8') as f:
        relations = json.load(f)

    print(f"关系数量: {len(relations)}")

    # 统计关系类型
    type_counts = defaultdict(int)
    for rel in relations:
        rel_type = rel.get('type', 'UNKNOWN')
        type_counts[rel_type] += 1

    print(f"\n关系类型分布:")
    for rel_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {rel_type}: {count:,}")

    return relations


def main():
    if len(sys.argv) > 2:
        entity_file = sys.argv[1]
        relation_file = sys.argv[2]
    elif len(sys.argv) > 1:
        # 只提供关系文件，尝试在同目录找实体文件
        relation_file = sys.argv[1]
        data_dir = Path(relation_file).parent
        entity_file = data_dir / "temp_en.json"
        print(f"自动查找实体文件: {entity_file}")
    else:
        # 使用默认路径
        data_dir = Path("/data/xuao/code_kg_search/linux_test/data")
        entity_file = data_dir / "temp_en.json"
        relation_file = data_dir / "all_relation.json"

    print(f"实体文件: {entity_file}")
    print(f"关系文件: {relation_file}\n")

    # 1. 加载实体
    entities = load_entities(entity_file)

    # 2. 加载关系
    relations = load_relations(relation_file)

    # 3. 建立函数索引
    function_by_name, function_by_id = build_function_index(entities)

    # 4. 建立调用图
    # 需要从relations列表中筛选CALLS关系
    calls_data = {'CALLS': [r for r in relations if r.get('type') == 'CALLS']}
    call_graph = build_call_graph(calls_data, function_by_id)

    # 5. 检查16节点路径
    if function_by_name and call_graph:
        check_16_node_path(function_by_name, call_graph, relations, function_by_id)

    print("\n" + "=" * 80)
    print("检查完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
