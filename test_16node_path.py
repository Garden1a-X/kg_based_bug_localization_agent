#!/usr/bin/env python3
"""
验证16节点完整调用链的测试脚本

测试从 dw_mci_pltfm_register 到 dw_mci_hi3660_execute_tuning 的完整路径
预期：16个节点，4个断点（间接调用）
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.kg_interface import KnowledgeGraphInterface
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<level>{message}</level>")


def test_16_node_path():
    """测试16节点的完整调用链"""
    print("=" * 80)
    print("测试16节点完整调用链")
    print("=" * 80)

    # 1. 加载知识图谱
    print("\n[1/4] 加载知识图谱...")
    # 使用和 run_mmc_case.py 一样的数据目录
    data_dir = "/data/xuao/code_kg_search/linux_test/data"
    kg = KnowledgeGraphInterface(data_dir=data_dir)

    # 2. 定义预期路径（16个节点）
    expected_path = [
        "dw_mci_pltfm_register",
        "dw_mci_probe",
        "dw_mci_init_slot",
        "mmc_add_host",              # 断点4: dw_mci_init_slot → mmc_add_host (Mock)
        "mmc_start_host",
        "_mmc_detect_change",
        "mmc_schedule_delayed_work",
        "mmc_rescan",                # 断点8: mmc_schedule_delayed_work → mmc_rescan (Mock)
        "mmc_rescan_try_freq",
        "mmc_attach_mmc",
        "mmc_init_card",
        "mmc_set_bus_speed",
        "mmc_set_timing",
        "mmc_execute_tuning",
        "dw_mci_execute_tuning",     # 断点14: mmc_execute_tuning → dw_mci_execute_tuning (Mock)
        "dw_mci_hi3660_execute_tuning"  # 断点15: dw_mci_execute_tuning → dw_mci_hi3660_execute_tuning (Mock)
    ]

    # 3. 检查每个节点是否存在
    print(f"\n[2/4] 检查16个节点是否存在...")
    missing_nodes = []
    for i, node_name in enumerate(expected_path, 1):
        entity = kg.find_function(node_name)
        if entity:
            print(f"  ✅ [{i:2d}] {node_name:<35} (ID: {entity['id']})")
        else:
            print(f"  ❌ [{i:2d}] {node_name:<35} (不存在)")
            missing_nodes.append(node_name)

    if missing_nodes:
        print(f"\n⚠️  发现 {len(missing_nodes)} 个缺失节点: {missing_nodes}")
        print("⚠️  路径可能不完整")
    else:
        print(f"\n✅ 所有16个节点都存在于图谱中")

    # 4. 检查相邻节点的连通性（包括Mock间接调用）
    print(f"\n[3/4] 检查相邻节点对的连通性（直接调用 + Mock间接调用）...")

    # Mock间接调用断点
    mock_breaks = {
        ("dw_mci_init_slot", "mmc_add_host"): 4,
        ("mmc_schedule_delayed_work", "mmc_rescan"): 8,
        ("mmc_execute_tuning", "dw_mci_execute_tuning"): 14,
        ("dw_mci_execute_tuning", "dw_mci_hi3660_execute_tuning"): 15,
    }

    reachable_count = 0
    unreachable_count = 0

    for i in range(len(expected_path) - 1):
        caller = expected_path[i]
        callee = expected_path[i + 1]

        # 检查是否是Mock断点
        is_mock = (caller, callee) in mock_breaks

        # 检查直接调用
        callees = kg.get_callees(caller, debug=False)
        is_reachable_direct = callee in callees

        # 检查Mock间接调用（使用私有方法 _find_indirect_callees）
        mock_indirect_callees = kg._find_indirect_callees(caller)
        is_reachable_mock = any(c == callee for c, _ in mock_indirect_callees)

        is_reachable = is_reachable_direct or is_reachable_mock

        if is_reachable:
            reachable_count += 1
            if is_mock:
                print(f"  ✅ [{i+1:2d}→{i+2:2d}] {caller:<35} → {callee:<35} (Mock间接调用)")
            else:
                print(f"  ✅ [{i+1:2d}→{i+2:2d}] {caller:<35} → {callee:<35} (直接调用)")
        else:
            unreachable_count += 1
            if is_mock:
                print(f"  ❌ [{i+1:2d}→{i+2:2d}] {caller:<35} → {callee:<35} (预期Mock，但未找到)")
            else:
                print(f"  ❌ [{i+1:2d}→{i+2:2d}] {caller:<35} → {callee:<35} (不可达)")

    print(f"\n连通性统计:")
    print(f"  ✅ 可达的相邻节点对: {reachable_count}/{len(expected_path)-1}")
    print(f"  ❌ 不可达的相邻节点对: {unreachable_count}/{len(expected_path)-1}")

    # 5. 执行BFS搜索
    print(f"\n[4/4] 执行BFS搜索（支持Mock间接调用）...")
    start_name = expected_path[0]
    end_name = expected_path[-1]

    result = kg.find_call_path_with_indirect(
        start=start_name,
        end=end_name,
        max_depth=20
    )

    if result and result.get('path'):
        path = result['path']
        edges = result.get('edges', [])

        print(f"\n✅ 找到路径! 长度: {len(path)} 个节点")
        print(f"\n路径详情:")

        # 统计间接调用
        indirect_count = sum(1 for e in edges if isinstance(e, dict) and e.get('type') == 'indirect')

        for i, node in enumerate(path):
            if i < len(path) - 1:
                edge = edges[i] if i < len(edges) else None
                if isinstance(edge, dict) and edge.get('type') == 'indirect':
                    bridge_info = edge.get('bridge', {})
                    bridge_type = bridge_info.get('bridge_type', 'unknown')
                    print(f"  [{i+1:2d}] {node:<35} --({bridge_type})-->")
                else:
                    print(f"  [{i+1:2d}] {node:<35} --------->")
            else:
                print(f"  [{i+1:2d}] {node:<35} (终点)")

        print(f"\n统计信息:")
        print(f"  节点数: {len(path)}")
        print(f"  间接调用数: {indirect_count}")

        # 与预期对比
        if len(path) == 16:
            print(f"\n✅ 路径长度匹配预期 (16个节点)")
        else:
            print(f"\n⚠️  路径长度与预期不符: 实际 {len(path)}, 预期 16")

        if indirect_count == 4:
            print(f"✅ 间接调用数匹配预期 (4个断点)")
        else:
            print(f"⚠️  间接调用数与预期不符: 实际 {indirect_count}, 预期 4")
    else:
        print(f"\n❌ 未找到路径!")
        print(f"起点: {start_name}")
        print(f"终点: {end_name}")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_16_node_path()
