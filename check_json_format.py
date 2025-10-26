#!/usr/bin/env python3
"""
检查知识图谱JSON文件的格式
帮助了解数据结构以便适配接口
"""
import json
from pathlib import Path
from collections import Counter


def check_json_format():
    """检查JSON文件格式"""
    
    # JSON文件路径
    data_dir = Path("/data/xuao/code_kg_search/linux_test/data")
    entity_file = data_dir / "temp_en.json"
    relation_file = data_dir / "relations.json"
    
    print("=" * 80)
    print("知识图谱JSON格式检查")
    print("=" * 80)
    
    # ==================== 检查实体文件 ====================
    print("\n【1】实体文件：temp_en.json")
    print("-" * 80)
    
    if not entity_file.exists():
        print(f"❌ 文件不存在: {entity_file}")
    else:
        print(f"✓ 文件存在: {entity_file}")
        print(f"✓ 文件大小: {entity_file.stat().st_size / 1024 / 1024:.2f} MB")
        
        with open(entity_file, 'r', encoding='utf-8') as f:
            entities = json.load(f)
        
        # 检查顶层结构
        print(f"\n顶层数据类型: {type(entities).__name__}")
        
        if isinstance(entities, dict):
            print(f"顶层字典的键: {list(entities.keys())[:10]}")
            print(f"总键数: {len(entities)}")
            
            # 检查每个键对应的数据
            for key, value in list(entities.items())[:3]:
                print(f"\n  键 '{key}' 的值类型: {type(value).__name__}")
                if isinstance(value, list):
                    print(f"    列表长度: {len(value)}")
                    if value:
                        print(f"    第一个元素: {value[0]}")
                elif isinstance(value, dict):
                    print(f"    字典键: {list(value.keys())[:10]}")
        
        elif isinstance(entities, list):
            print(f"列表长度: {len(entities)}")
            if entities:
                print(f"\n第一个元素类型: {type(entities[0]).__name__}")
                print(f"第一个元素: {entities[0]}")
        
        # 统计实体类型
        print("\n实体类型统计:")
        if isinstance(entities, dict):
            # 如果是字典，可能按类型分组
            for entity_type, entity_list in entities.items():
                if isinstance(entity_list, list):
                    print(f"  {entity_type}: {len(entity_list)} 个")
                    if entity_list:
                        print(f"    示例: {entity_list[0]}")
        elif isinstance(entities, list):
            # 如果是列表，统计type字段
            type_counter = Counter()
            for entity in entities:
                if isinstance(entity, dict):
                    entity_type = entity.get('type') or entity.get('entity_type') or entity.get('label') or 'unknown'
                    type_counter[entity_type] += 1
            
            for entity_type, count in type_counter.most_common(10):
                print(f"  {entity_type}: {count} 个")
        
        # 显示几个完整的实体示例
        print("\n实体示例（前3个）:")
        sample_entities = []
        if isinstance(entities, dict):
            for key, value in entities.items():
                if isinstance(value, list) and value:
                    sample_entities.extend(value[:1])
                if len(sample_entities) >= 3:
                    break
        elif isinstance(entities, list):
            sample_entities = entities[:3]
        
        for i, entity in enumerate(sample_entities, 1):
            print(f"\n  示例 {i}:")
            print(f"  {json.dumps(entity, indent=4, ensure_ascii=False)[:500]}")
    
    # ==================== 检查关系文件 ====================
    print("\n" + "=" * 80)
    print("【2】关系文件：relations.json")
    print("-" * 80)
    
    if not relation_file.exists():
        print(f"❌ 文件不存在: {relation_file}")
    else:
        print(f"✓ 文件存在: {relation_file}")
        print(f"✓ 文件大小: {relation_file.stat().st_size / 1024 / 1024:.2f} MB")
        
        with open(relation_file, 'r', encoding='utf-8') as f:
            relations = json.load(f)
        
        # 检查顶层结构
        print(f"\n顶层数据类型: {type(relations).__name__}")
        
        if isinstance(relations, dict):
            print(f"顶层字典的键: {list(relations.keys())[:10]}")
            print(f"总键数: {len(relations)}")
            
            # 检查每个键对应的数据
            for key, value in list(relations.items())[:3]:
                print(f"\n  键 '{key}' 的值类型: {type(value).__name__}")
                if isinstance(value, list):
                    print(f"    列表长度: {len(value)}")
                    if value:
                        print(f"    第一个元素: {value[0]}")
                elif isinstance(value, dict):
                    print(f"    字典键: {list(value.keys())[:10]}")
        
        elif isinstance(relations, list):
            print(f"列表长度: {len(relations)}")
            if relations:
                print(f"\n第一个元素类型: {type(relations[0]).__name__}")
                print(f"第一个元素: {relations[0]}")
        
        # 统计关系类型
        print("\n关系类型统计:")
        if isinstance(relations, dict):
            # 如果是字典，可能按关系类型分组
            for rel_type, rel_list in relations.items():
                if isinstance(rel_list, list):
                    print(f"  {rel_type}: {len(rel_list)} 个")
                    if rel_list:
                        print(f"    示例: {rel_list[0]}")
        elif isinstance(relations, list):
            # 如果是列表，统计type字段
            type_counter = Counter()
            for relation in relations:
                if isinstance(relation, dict):
                    rel_type = relation.get('type') or relation.get('relation_type') or relation.get('label') or 'unknown'
                    type_counter[rel_type] += 1
            
            for rel_type, count in type_counter.most_common(10):
                print(f"  {rel_type}: {count} 个")
        
        # 显示几个完整的关系示例
        print("\n关系示例（前3个）:")
        sample_relations = []
        if isinstance(relations, dict):
            for key, value in relations.items():
                if isinstance(value, list) and value:
                    sample_relations.extend(value[:1])
                if len(sample_relations) >= 3:
                    break
        elif isinstance(relations, list):
            sample_relations = relations[:3]
        
        for i, relation in enumerate(sample_relations, 1):
            print(f"\n  示例 {i}:")
            print(f"  {json.dumps(relation, indent=4, ensure_ascii=False)[:500]}")
    
    # ==================== 查找MMC相关函数 ====================
    print("\n" + "=" * 80)
    print("【3】查找MMC相关函数")
    print("-" * 80)
    
    if entity_file.exists():
        with open(entity_file, 'r', encoding='utf-8') as f:
            entities = json.load(f)
        
        # 查找包含 mmc 的函数
        mmc_functions = []
        
        if isinstance(entities, dict):
            # 字典格式，可能有 'Function' 键
            for key, value in entities.items():
                if 'function' in key.lower() and isinstance(value, list):
                    for entity in value:
                        if isinstance(entity, dict):
                            name = entity.get('name', '')
                            if 'mmc' in name.lower() or 'dw_mci' in name.lower():
                                mmc_functions.append(entity)
        elif isinstance(entities, list):
            # 列表格式
            for entity in entities:
                if isinstance(entity, dict):
                    entity_type = entity.get('type') or entity.get('entity_type') or ''
                    name = entity.get('name', '')
                    if 'function' in entity_type.lower():
                        if 'mmc' in name.lower() or 'dw_mci' in name.lower():
                            mmc_functions.append(entity)
        
        if mmc_functions:
            print(f"✓ 找到 {len(mmc_functions)} 个MMC相关函数")
            print("\n前10个MMC函数:")
            for i, func in enumerate(mmc_functions[:10], 1):
                print(f"  {i}. {func.get('name', 'N/A')}")
        else:
            print("❌ 未找到MMC相关函数")
            print("提示：可能需要调整搜索条件")
    
    print("\n" + "=" * 80)
    print("检查完成！")
    print("=" * 80)


if __name__ == "__main__":
    try:
        check_json_format()
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
