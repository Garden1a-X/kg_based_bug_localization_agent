"""
路径搜索调试工具

用于诊断路径搜索失败的原因，逐步显示BFS搜索过程
"""
import sys
from pathlib import Path
from collections import deque

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.kg_interface import KnowledgeGraphInterface
from data.mock_indirect_calls import get_mock_indirect_callees


def debug_path_search(data_dir: str, start_func: str, end_func: str, max_steps: int = 10):
    """
    诊断路径搜索过程

    Args:
        data_dir: 数据目录
        start_func: 起点函数名
        end_func: 终点函数名
        max_steps: 显示的最大步数
    """
    kg = KnowledgeGraphInterface(data_dir)

    print("=" * 80)
    print("路径搜索详细诊断")
    print("=" * 80)

    # 1. 基础信息
    start_entity = kg.find_function(start_func)
    end_entity = kg.find_function(end_func)

    if not start_entity:
        print(f"错误: 找不到起点函数 '{start_func}'")
        kg.close()
        return

    if not end_entity:
        print(f"错误: 找不到终点函数 '{end_func}'")
        kg.close()
        return

    start_id = kg.normalize_id(start_entity['id'])
    end_id = kg.normalize_id(end_entity['id'])

    print(f"\n起点: {start_func}")
    print(f"  ID: {start_id}")
    print(f"  文件: {start_entity.get('source_file', 'Unknown')}")

    print(f"\n终点: {end_func}")
    print(f"  ID: {end_id}")
    print(f"  文件: {end_entity.get('source_file', 'Unknown')}")

    # 2. 检查终点等价ID
    end_equivalent_ids = kg.get_equivalent_ids(end_id)
    print(f"\n终点等价ID: {end_equivalent_ids}")

    # 3. 检查起点的邻居
    print(f"\n检查起点的直接调用:")
    callees_with_lines = kg._get_callees_with_lines(start_id)
    print(f"  _get_callees_with_lines 返回: {len(callees_with_lines)} 个")

    if callees_with_lines:
        print(f"  前5个被调用者:")
        for i, (callee_name, call_line) in enumerate(callees_with_lines[:5]):
            print(f"    {i+1}. {callee_name} (line {call_line})")
    else:
        print(f"  ⚠️  起点没有任何直接调用！")

        # 进一步诊断
        print(f"\n进一步诊断:")
        start_equiv_ids = kg.get_equivalent_ids(start_id)
        print(f"  起点等价ID: {start_equiv_ids}")

        for equiv_id in start_equiv_ids:
            if equiv_id in kg.call_graph_with_lines:
                print(f"    ✓ {equiv_id} 在 call_graph_with_lines 中")
                print(f"      被调用者: {len(kg.call_graph_with_lines[equiv_id])} 个")
            else:
                print(f"    ✗ {equiv_id} 不在 call_graph_with_lines 中")

    # 4. 检查Mock数据
    print(f"\n检查间接调用 (Mock数据):")
    indirect_callees = get_mock_indirect_callees(start_func)
    if indirect_callees:
        print(f"  找到 {len(indirect_callees)} 个Mock间接调用:")
        for callee_name, bridge_info in indirect_callees:
            print(f"    - {callee_name} ({bridge_info.get('bridge_type')})")
    else:
        print(f"  起点没有Mock间接调用")

    # 5. 手动BFS搜索
    print(f"\n" + "=" * 80)
    print(f"开始BFS搜索 (显示前 {max_steps} 步)")
    print("=" * 80)

    queue = deque([(start_id, [start_id], [], [])])
    visited_at_depth = {}
    step = 0
    found = False

    while queue and step < max_steps and not found:
        step += 1
        current_id, path_ids, edge_types, call_lines = queue.popleft()
        current_depth = len(path_ids)

        current_entity = kg.entity_by_id.get(current_id)
        current_name = current_entity['name'] if current_entity else 'Unknown'

        print(f"\n步骤 {step}:")
        print(f"  当前节点: {current_name}")
        print(f"  当前深度: {current_depth}")

        # 检查是否到达终点
        if current_id in end_equivalent_ids:
            print(f"  ✓✓✓ 找到目标函数！")
            path_names = [kg.entity_by_id.get(pid, {}).get('name', 'Unknown') for pid in path_ids]
            print(f"  路径: {' -> '.join(path_names)}")
            found = True
            break

        # 检查visited_at_depth
        if current_id in visited_at_depth:
            prev_depth = visited_at_depth[current_id]
            if current_depth >= prev_depth + 3:
                print(f"  跳过 (之前在深度 {prev_depth} 访问过)")
                continue

        visited_at_depth[current_id] = min(
            visited_at_depth.get(current_id, float('inf')),
            current_depth
        )

        # 获取邻居
        direct_callees = kg._get_callees_with_lines(current_id)
        indirect_callees = get_mock_indirect_callees(current_name)

        print(f"  邻居: 直接调用 {len(direct_callees)} 个, 间接调用 {len(indirect_callees)} 个")

        added = 0

        # 添加直接调用
        for callee_name, callee_line in direct_callees:
            callee_entity = kg.find_function(callee_name)
            if not callee_entity:
                continue

            callee_id = kg.normalize_id(callee_entity['id'])
            if not callee_id or callee_id in path_ids:
                continue

            queue.append((
                callee_id,
                path_ids + [callee_id],
                edge_types + ['direct'],
                call_lines + [callee_line]
            ))
            added += 1

            if added <= 3:
                print(f"    + {callee_name} (direct, line {callee_line})")

        # 添加间接调用
        for callee_name, bridge_info in indirect_callees:
            callee_entity = kg.find_function(callee_name)
            if not callee_entity:
                continue

            callee_id = kg.normalize_id(callee_entity['id'])
            if not callee_id or callee_id in path_ids:
                continue

            queue.append((
                callee_id,
                path_ids + [callee_id],
                edge_types + [{'type': 'indirect', 'bridge': bridge_info}],
                call_lines + [None]
            ))
            added += 1
            print(f"    + {callee_name} (indirect, {bridge_info.get('bridge_type')})")

        if added > 3:
            print(f"    ... 还有 {added - 3} 个节点")

        print(f"  队列大小: {len(queue)}")

    # 6. 搜索结果
    print(f"\n" + "=" * 80)
    if found:
        print("✓ 成功找到路径！")
    elif step >= max_steps:
        print(f"达到最大显示步数 {max_steps}")
        print(f"队列中还有 {len(queue)} 个待探索节点")
        print(f"已访问 {len(visited_at_depth)} 个不同节点")
        print("继续搜索可能能找到路径")
    else:
        print("✗ 搜索失败，队列为空")
        print(f"已访问 {len(visited_at_depth)} 个不同节点")

    print("=" * 80)

    kg.close()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='路径搜索诊断工具')
    parser.add_argument('--data-dir', default='/data/xuao/code_kg_search/linux_test/data/mmc',
                        help='数据目录')
    parser.add_argument('--start', default='dw_mci_pltfm_probe',
                        help='起点函数名')
    parser.add_argument('--end', default='dw_mci_execute_tuning',
                        help='终点函数名')
    parser.add_argument('--max-steps', type=int, default=10,
                        help='显示的最大步数')

    args = parser.parse_args()

    debug_path_search(
        data_dir=args.data_dir,
        start_func=args.start,
        end_func=args.end,
        max_steps=args.max_steps
    )


if __name__ == "__main__":
    main()
