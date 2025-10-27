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


def check_16_node_path(function_by_name, call_graph):
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

    return reachable, unreachable


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


def main():
    if len(sys.argv) > 1:
        graph_file = sys.argv[1]
    else:
        graph_file = "/data/xuao/code_kg_search/linux_test/data/all_relation.json"

    print(f"检查图谱文件: {graph_file}\n")

    # 1. 检查格式
    data = check_new_graph_format(graph_file)

    # 2. 建立索引
    function_by_name, function_by_id = build_function_index(data)

    # 3. 建立调用图
    call_graph = build_call_graph(data, function_by_id)

    # 4. 检查16节点路径
    if function_by_name and call_graph:
        check_16_node_path(function_by_name, call_graph)

    # 5. 检查关系类型
    check_relation_types(data)

    print("\n" + "=" * 80)
    print("检查完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
