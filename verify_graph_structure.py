"""
快速验证图谱结构是否符合新的间接调用格式
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.kg_interface import KnowledgeGraphInterface


def verify_graph_structure(data_dir: str):
    """验证图谱结构"""
    print("=" * 70)
    print("验证图谱结构")
    print("=" * 70)
    print(f"\n数据目录: {data_dir}\n")

    # 加载图谱
    kg = KnowledgeGraphInterface(data_dir)

    # 1. 检查基本统计
    print("1️⃣  图谱基本统计:")
    print("-" * 70)
    stats = kg.get_database_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 2. 检查 CALLS 关系结构
    print("\n2️⃣  检查 CALLS 关系结构:")
    print("-" * 70)

    if 'CALLS' not in kg.relations:
        print("  ❌ 图谱中没有 CALLS 关系")
        kg.close()
        return False

    calls = kg.relations['CALLS']
    print(f"  总 CALLS 关系数: {len(calls)}")

    # 检查新字段
    with_call_type = [r for r in calls if 'call_type' in r]
    indirect_calls = [r for r in calls if r.get('call_type') == 'indirect']
    with_field_path = [r for r in calls if 'field_path' in r]

    print(f"  包含 call_type 字段: {len(with_call_type)}")
    print(f"  间接调用 (call_type=indirect): {len(indirect_calls)}")
    print(f"  包含 field_path 字段: {len(with_field_path)}")

    # 3. 检查 ASSIGNED_TO 关系
    print("\n3️⃣  检查 ASSIGNED_TO 关系:")
    print("-" * 70)

    if 'ASSIGNED_TO' not in kg.relations:
        print("  ❌ 图谱中没有 ASSIGNED_TO 关系")
    else:
        assigned_to = kg.relations['ASSIGNED_TO']
        print(f"  总 ASSIGNED_TO 关系数: {len(assigned_to)}")

    # 4. 显示示例间接调用
    if indirect_calls:
        print("\n4️⃣  示例间接调用（前3个）:")
        print("-" * 70)

        for i, rel in enumerate(indirect_calls[:3]):
            head_id = rel.get('head')
            tail_id = rel.get('tail')
            field_path = rel.get('field_path', [])
            target_type = rel.get('target_type')

            # 获取实体信息
            head_entity = kg.entity_by_id.get(head_id, {})
            tail_entity = kg.entity_by_id.get(tail_id, {})

            print(f"\n  示例 #{i+1}:")
            print(f"    调用者: {head_entity.get('name', f'ID:{head_id}')}")
            print(f"    目标类型: {target_type}")
            print(f"    目标: {tail_entity.get('name', f'ID:{tail_id}')} ({tail_entity.get('type', 'unknown')})")
            print(f"    字段路径: {field_path}")

            # 测试查询 ASSIGNED_TO
            if field_path:
                field_name = field_path[-1]
                print(f"    查询字段名 '{field_name}' 的 ASSIGNED_TO:")
                targets = kg.query_assigned_to_by_field_name(field_name)
                if targets:
                    print(f"      ✓ 找到 {len(targets)} 个目标函数: {', '.join(targets[:5])}")
                else:
                    print(f"      ✗ 未找到目标函数")

    else:
        print("\n⚠️  警告: 图谱中没有间接调用")
        print("  这可能意味着：")
        print("  1. 图谱还未更新到新结构")
        print("  2. 或者该子图中确实没有间接调用")

    # 5. 测试一个简单的路径搜索
    print("\n5️⃣  测试路径搜索:")
    print("-" * 70)

    # 尝试找两个存在的函数
    if 'FUNCTION' in kg.entities and len(kg.entities['FUNCTION']) >= 2:
        func_names = list(kg.entities['FUNCTION'].keys())
        start = func_names[0]
        end = func_names[min(10, len(func_names)-1)]  # 选一个稍远的函数

        print(f"  测试: {start} -> {end}")

        paths = kg.find_top_k_call_paths_with_indirect(
            start=start,
            end=end,
            max_depth=20,
            k=1,
            debug=False
        )

        if paths:
            print(f"  ✓ 找到路径: 长度={paths[0]['length']}, 间接调用={paths[0]['indirect_count']}")
        else:
            print(f"  ✗ 未找到路径")
    else:
        print("  跳过测试（函数数量不足）")

    kg.close()

    print("\n" + "=" * 70)
    print("✅ 验证完成")
    print("=" * 70)

    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        # 尝试几个可能的路径
        possible_paths = [
            "/data/xuao/code_kg_search/linux_test/data/mmc",
            "/data/xuao/code_kg_search/linux_test/data",
            "./data"
        ]

        data_dir = None
        for path in possible_paths:
            from pathlib import Path
            if Path(path).exists():
                data_dir = path
                break

        if not data_dir:
            print("❌ 未找到图谱数据目录")
            print("\n用法: python verify_graph_structure.py <数据目录路径>")
            print("\n或者设置环境变量: export KG_DATA_DIR=<数据目录路径>")
            sys.exit(1)

    verify_graph_structure(data_dir)
