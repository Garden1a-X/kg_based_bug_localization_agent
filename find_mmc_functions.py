#!/usr/bin/env python3
"""
查找特定的MMC函数
"""
import json
from pathlib import Path


def find_specific_functions():
    """查找我们需要的函数"""
    
    data_dir = Path("/data/xuao/code_kg_search/linux_test/data")
    entity_file = data_dir / "temp_en.json"
    
    # 要查找的函数
    target_functions = [
        'dw_mci_pltfm_probe',
        'dw_mci_probe', 
        'dw_mci_execute_tuning',
        'dw_mci_hi3660_execute_tuning',
        'mmc_start_host',
        'mmc_rescan',
        'mmc_attach_mmc',
        'mmc_init_card',
        'mmc_set_timing'
    ]
    
    print("查找特定MMC函数...")
    print("=" * 80)
    
    with open(entity_file, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    
    # 查找函数
    found_functions = {}
    
    for entity in entities:
        if entity.get('type') == 'FUNCTION':
            name = entity.get('name', '')
            if name in target_functions:
                found_functions[name] = entity
                print(f"✓ 找到: {name}")
                print(f"  ID: {entity.get('id')}")
                print(f"  文件: {entity.get('source_file', 'N/A')}")
                print()
    
    # 检查缺失的函数
    print("\n" + "=" * 80)
    print("检查结果:")
    print("-" * 80)
    
    for func in target_functions:
        if func in found_functions:
            print(f"✓ {func}")
        else:
            print(f"✗ {func} - 未找到")
    
    print("\n" + "=" * 80)
    print(f"找到: {len(found_functions)}/{len(target_functions)}")
    print("=" * 80)
    
    # 如果没找全，搜索相似的
    if len(found_functions) < len(target_functions):
        print("\n搜索相似的函数名...")
        print("-" * 80)
        
        missing = set(target_functions) - set(found_functions.keys())
        
        for missing_func in missing:
            print(f"\n查找包含 '{missing_func[:10]}' 的函数:")
            similar = []
            for entity in entities:
                if entity.get('type') == 'FUNCTION':
                    name = entity.get('name', '')
                    if missing_func[:10] in name:
                        similar.append(name)
                        if len(similar) >= 5:
                            break
            
            if similar:
                for name in similar:
                    print(f"  - {name}")
            else:
                print(f"  未找到相似函数")


if __name__ == "__main__":
    find_specific_functions()
