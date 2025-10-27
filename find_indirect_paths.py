#!/usr/bin/env python3
"""
系统性地查找4个不可达节点对之间的间接路径
尝试多种连接模式：2跳、3跳、不同关系类型组合
"""
import json
import sys
from pathlib import Path
from collections import defaultdict, deque

def load_data(entity_file, relation_file):
    """加载数据"""
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

    for entity in entities:
        entity_id = str(entity.get('id'))
        entity_by_id[entity_id] = entity

        if entity.get('type') == 'FUNCTION':
            name = entity.get('name')
            if name:
                if name not in function_by_name:
                    function_by_name[name] = []
                function_by_name[name].append(entity)

    # 按关系类型分组
    relations_by_type = defaultdict(list)
    for rel in relations:
        rel_type = rel.get('type')
        relations_by_type[rel_type].append(rel)

    # 构建邻接表 (head -> [(tail, rel_type, rel)])
    forward_graph = defaultdict(list)
    backward_graph = defaultdict(list)

    for rel in relations:
        head = str(rel.get('head'))
        tail = str(rel.get('tail'))
        rel_type = rel.get('type')

        forward_graph[head].append((tail, rel_type, rel))
        backward_graph[tail].append((head, rel_type, rel))

    print(f"函数数量: {len(function_by_name)}")
    print(f"实体总数: {len(entity_by_id)}")
    print(f"关系类型数: {len(relations_by_type)}")

    return function_by_name, entity_by_id, relations_by_type, forward_graph, backward_graph

def find_paths_bfs(start_ids, end_ids, forward_graph, entity_by_id, max_depth=4):
    """BFS查找从start到end的所有路径（限制深度）"""
    paths_found = []

    for start_id in start_ids:
        # BFS
        queue = deque([(start_id, [start_id], [])])  # (当前节点, 路径, 关系)
        visited = {start_id: 0}  # 节点 -> 到达该节点的最短距离

        while queue:
            current_id, path, rel_path = queue.popleft()
            current_depth = len(path) - 1

            if current_depth >= max_depth:
                continue

            # 检查是否到达目标
            if current_id in end_ids:
                paths_found.append((path, rel_path))
                continue  # 继续搜索其他路径

            # 扩展邻居
            for next_id, rel_type, rel in forward_graph.get(current_id, []):
                next_depth = current_depth + 1

                # 只访问未访问或找到更短路径的节点
                if next_id not in visited or visited[next_id] > next_depth:
                    visited[next_id] = next_depth
                    new_path = path + [next_id]
                    new_rel_path = rel_path + [(rel_type, rel)]
                    queue.append((next_id, new_path, new_rel_path))

    return paths_found

def analyze_paths(paths, entity_by_id):
    """分析路径模式"""
    if not paths:
        return None

    # 按路径长度分组
    by_length = defaultdict(list)
    for path_ids, rel_path in paths:
        by_length[len(path_ids)].append((path_ids, rel_path))

    # 按关系模式分组
    by_pattern = defaultdict(list)
    for path_ids, rel_path in paths:
        pattern = " → ".join([rel_type for rel_type, _ in rel_path])
        by_pattern[pattern].append((path_ids, rel_path))

    # 统计中间节点类型
    intermediate_types = defaultdict(int)
    for path_ids, rel_path in paths:
        for node_id in path_ids[1:-1]:  # 排除起点和终点
            entity = entity_by_id.get(node_id, {})
            entity_type = entity.get('type', 'UNKNOWN')
            intermediate_types[entity_type] += 1

    return {
        'by_length': dict(by_length),
        'by_pattern': dict(by_pattern),
        'intermediate_types': dict(intermediate_types)
    }

def format_path(path_ids, rel_path, entity_by_id):
    """格式化路径显示"""
    result = []
    for i, node_id in enumerate(path_ids):
        entity = entity_by_id.get(node_id, {})
        entity_type = entity.get('type', 'UNKNOWN')
        entity_name = entity.get('name', f'ID:{node_id}')

        result.append(f"{entity_name}({entity_type})")

        if i < len(rel_path):
            rel_type, _ = rel_path[i]
            result.append(f" --[{rel_type}]--> ")

    return "".join(result)

def check_pair(func_a_name, func_b_name, function_by_name, entity_by_id, forward_graph, backward_graph):
    """检查一对函数之间的所有可能路径"""
    print(f"\n{'='*80}")
    print(f"检查: {func_a_name} → {func_b_name}")
    print(f"{'='*80}")

    # 获取函数ID
    func_a_entities = function_by_name.get(func_a_name, [])
    func_b_entities = function_by_name.get(func_b_name, [])

    if not func_a_entities or not func_b_entities:
        print("❌ 函数不存在")
        return

    func_a_ids = {str(e.get('id')) for e in func_a_entities}
    func_b_ids = {str(e.get('id')) for e in func_b_entities}

    print(f"\n函数A: {len(func_a_ids)} 个ID: {func_a_ids}")
    print(f"函数B: {len(func_b_ids)} 个ID: {func_b_ids}")

    # 查找路径 (最多4跳)
    print(f"\n[1] BFS搜索路径 (最多4跳)...")
    paths = find_paths_bfs(func_a_ids, func_b_ids, forward_graph, entity_by_id, max_depth=4)

    if not paths:
        print(f"  ❌ 未找到路径")
        return

    print(f"  ✅ 找到 {len(paths)} 条路径")

    # 分析路径
    analysis = analyze_paths(paths, entity_by_id)

    # 按长度统计
    print(f"\n[2] 按路径长度统计:")
    for length in sorted(analysis['by_length'].keys()):
        count = len(analysis['by_length'][length])
        print(f"  {length}跳: {count} 条")

    # 按模式统计
    print(f"\n[3] 按关系模式统计 (前10种):")
    patterns = sorted(analysis['by_pattern'].items(), key=lambda x: len(x[1]), reverse=True)
    for i, (pattern, path_list) in enumerate(patterns[:10], 1):
        print(f"  [{i}] {pattern}: {len(path_list)} 条")

    # 中间节点类型
    print(f"\n[4] 中间节点类型统计:")
    for entity_type, count in sorted(analysis['intermediate_types'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {entity_type}: {count} 次")

    # 显示最短路径示例
    print(f"\n[5] 最短路径示例 (前3条):")
    shortest_length = min(analysis['by_length'].keys())
    shortest_paths = analysis['by_length'][shortest_length][:3]

    for i, (path_ids, rel_path) in enumerate(shortest_paths, 1):
        print(f"\n  路径 {i}:")
        print(f"  {format_path(path_ids, rel_path, entity_by_id)}")

    # 显示最常见模式的示例
    if patterns:
        most_common_pattern, most_common_paths = patterns[0]
        print(f"\n[6] 最常见模式示例: {most_common_pattern}")
        for i, (path_ids, rel_path) in enumerate(most_common_paths[:2], 1):
            print(f"\n  示例 {i}:")
            print(f"  {format_path(path_ids, rel_path, entity_by_id)}")

    return analysis

def main():
    data_dir = Path("/data/xuao/code_kg_search/linux_test/data")
    entity_file = data_dir / "temp_en.json"
    relation_file = data_dir / "all_relation.json"

    # 加载数据
    entities, relations = load_data(entity_file, relation_file)

    # 建立索引
    function_by_name, entity_by_id, relations_by_type, forward_graph, backward_graph = build_indexes(entities, relations)

    # 4个不可达节点对
    pairs = [
        ("dw_mci_init_slot", "mmc_add_host"),
        ("mmc_schedule_delayed_work", "mmc_rescan"),
        ("mmc_execute_tuning", "dw_mci_execute_tuning"),
        ("dw_mci_execute_tuning", "dw_mci_hi3660_execute_tuning"),
    ]

    # 检查每一对
    results = {}
    for func_a, func_b in pairs:
        result = check_pair(func_a, func_b, function_by_name, entity_by_id, forward_graph, backward_graph)
        results[(func_a, func_b)] = result

    # 总结
    print(f"\n{'='*80}")
    print("总结")
    print(f"{'='*80}")

    for (func_a, func_b), result in results.items():
        if result:
            shortest = min(result['by_length'].keys())
            total = sum(len(paths) for paths in result['by_length'].values())
            print(f"\n{func_a} → {func_b}:")
            print(f"  ✅ 找到 {total} 条路径，最短 {shortest} 跳")

            # 显示最短路径的模式
            shortest_paths = result['by_length'][shortest]
            patterns = set()
            for _, rel_path in shortest_paths:
                pattern = " → ".join([rel_type for rel_type, _ in rel_path])
                patterns.add(pattern)
            print(f"  最短路径模式: {', '.join(list(patterns)[:3])}")
        else:
            print(f"\n{func_a} → {func_b}: ❌ 未找到路径")

if __name__ == "__main__":
    main()
