"""
诊断函数的ID映射问题
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.kg_interface import KnowledgeGraphInterface


def debug_function_ids(data_dir: str, func_name: str):
    """
    诊断函数的ID映射

    Args:
        data_dir: 数据目录
        func_name: 函数名
    """
    kg = KnowledgeGraphInterface(data_dir)

    print("=" * 80)
    print(f"函数ID映射诊断: {func_name}")
    print("=" * 80)

    # 1. 查找函数实体
    print(f"\n1. find_function('{func_name}'):")
    entity = kg.find_function(func_name)
    if entity:
        print(f"   找到实体:")
        print(f"     ID: {entity.get('id')}")
        print(f"     名称: {entity.get('name')}")
        print(f"     文件: {entity.get('source_file', entity.get('file', 'Unknown'))}")
        print(f"     is_declaration: {entity.get('is_declaration', 'N/A')}")
        main_id = entity.get('id')
    else:
        print(f"   ✗ 找不到函数 {func_name}")
        kg.close()
        return

    # 2. 查找该函数名的所有ID
    print(f"\n2. func_name_to_ids['{func_name}']:")
    all_ids = kg.func_name_to_ids.get(func_name, [])
    print(f"   该函数名对应 {len(all_ids)} 个ID:")
    for i, func_id in enumerate(all_ids):
        entity = kg.entity_by_id.get(func_id)
        if entity:
            is_decl = entity.get('is_declaration', 'N/A')
            file_path = entity.get('source_file', entity.get('file', 'Unknown'))
            print(f"     {i+1}. ID={func_id}, is_declaration={is_decl}")
            print(f"        文件: {file_path}")

    # 3. 对于main_id，查看normalize_id的结果
    print(f"\n3. normalize_id('{main_id}'):")
    normalized_id = kg.normalize_id(main_id)
    if normalized_id != main_id:
        print(f"   {main_id} -> {normalized_id} (changed)")
    else:
        print(f"   {main_id} (unchanged)")

    # 4. 对于main_id，查看get_equivalent_ids的结果
    print(f"\n4. get_equivalent_ids('{main_id}'):")
    equiv_ids = kg.get_equivalent_ids(main_id)
    print(f"   等价ID集合: {equiv_ids}")

    # 5. 检查call_graph_with_lines
    print(f"\n5. call_graph_with_lines 中的信息:")
    found_in_call_graph = False

    # 检查所有ID
    print(f"   检查所有ID是否在 call_graph_with_lines 中:")
    for func_id in all_ids:
        if func_id in kg.call_graph_with_lines:
            found_in_call_graph = True
            callees = kg.call_graph_with_lines[func_id]
            print(f"     ✓ {func_id}: {len(callees)} 个被调用者")
            for i, callee_info in enumerate(callees[:3]):
                callee_id = kg.normalize_id(callee_info['callee_id'])
                callee_entity = kg.entity_by_id.get(callee_id)
                callee_name = callee_entity['name'] if callee_entity else 'Unknown'
                print(f"         {i+1}. {callee_name} (line {callee_info.get('call_line')})")
            if len(callees) > 3:
                print(f"         ... 还有 {len(callees) - 3} 个")
        else:
            print(f"     ✗ {func_id}: 不在 call_graph_with_lines 中")

    # 6. 检查等价ID
    print(f"\n   检查等价ID是否在 call_graph_with_lines 中:")
    for equiv_id in equiv_ids:
        if equiv_id in kg.call_graph_with_lines:
            callees = kg.call_graph_with_lines[equiv_id]
            print(f"     ✓ {equiv_id}: {len(callees)} 个被调用者")
        else:
            print(f"     ✗ {equiv_id}: 不在 call_graph_with_lines 中")

    if not found_in_call_graph:
        print(f"   ⚠️  该函数的任何ID都不在 call_graph_with_lines 中！")

    # 7. 直接在 relations['CALLS'] 中搜索
    print(f"\n6. 在 relations['CALLS'] 中直接搜索:")
    calls_from_func = []
    if 'CALLS' in kg.relations:
        for rel in kg.relations['CALLS']:
            head = rel.get('head')
            if head in all_ids:
                tail = rel.get('tail')
                call_line = rel.get('call_line')

                # 查找 tail 对应的函数名
                tail_entity = kg.entity_by_id.get(tail)
                tail_name = tail_entity['name'] if tail_entity else 'Unknown'

                calls_from_func.append({
                    'head': head,
                    'tail': tail,
                    'tail_name': tail_name,
                    'call_line': call_line
                })

    if calls_from_func:
        print(f"   在 CALLS 关系中找到 {len(calls_from_func)} 条该函数的调用:")
        for i, call in enumerate(calls_from_func[:5]):
            print(f"     {i+1}. {func_name}(ID={call['head']}) -> {call['tail_name']}(ID={call['tail']}) at line {call['call_line']}")
        if len(calls_from_func) > 5:
            print(f"     ... 还有 {len(calls_from_func) - 5} 条")
    else:
        print(f"   ✗ 在 CALLS 关系中找不到该函数的调用")

    # 8. 检查声明-实现映射
    print(f"\n7. 声明-实现映射:")
    print(f"   decl_to_impl:")
    for func_id in all_ids:
        if func_id in kg.decl_to_impl:
            impl_id = kg.decl_to_impl[func_id]
            print(f"     {func_id} -> {impl_id}")
        else:
            print(f"     {func_id}: (不在 decl_to_impl 中)")

    print(f"\n   impl_to_decl:")
    for func_id in all_ids:
        if func_id in kg.impl_to_decl:
            decl_ids = kg.impl_to_decl[func_id]
            print(f"     {func_id} <- {decl_ids}")
        else:
            print(f"     {func_id}: (不在 impl_to_decl 中)")

    print("\n" + "=" * 80)

    kg.close()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='函数ID映射诊断工具')
    parser.add_argument('--data-dir', default='/data/xuao/code_kg_search/linux_test/data/mmc',
                        help='数据目录')
    parser.add_argument('--func', required=True,
                        help='函数名')

    args = parser.parse_args()

    debug_function_ids(
        data_dir=args.data_dir,
        func_name=args.func
    )


if __name__ == "__main__":
    main()
