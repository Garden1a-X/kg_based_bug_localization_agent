"""
演示Top-K路径搜索功能
展示如何使用call_line剪枝和返回多条路径
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from coordinator.master_coordinator import MasterCoordinator
from utils.logger import setup_logger, print_header
import json

# 配置日志
setup_logger()


def run_mmc_case_topk():
    """运行MMC案例 - Top-K路径搜索"""

    # 甲方提供的错误日志（3行简单日志）
    mmc_error_log = """
ALL phases bad!
mmc0: tuning execution failed: -1
mmc0: error -1 whilst initialising MMC card
    """

    print_header("运行MMC案例 - Top-K路径搜索")

    # 指定数据目录（优先使用MMC子图）
    data_dir = "/data/xuao/code_kg_search/linux_test/data/mmc"

    # 如果MMC子图不存在，回退到完整数据
    if not os.path.exists(data_dir):
        data_dir = "/data/xuao/code_kg_search/linux_test/data"
        print(f"注意: MMC子图不存在，使用完整图谱 ({data_dir})")

    # 创建协调器（不启用LLM）
    coordinator = MasterCoordinator(data_dir=data_dir, llm_client=None)

    try:
        # ========== 方式1：自动推断起止点，返回Top-K路径 ==========
        print("\n[方式1] 自动推断 + Top-5路径:")
        print("=" * 60)
        result1 = coordinator.process_top_k(
            mmc_error_log,
            k=5  # 返回最多5条路径
        )

        # 保存结果
        output_dir = project_root / 'output'
        output_dir.mkdir(exist_ok=True)

        with open(output_dir / 'mmc_case_topk_auto.json', 'w', encoding='utf-8') as f:
            json.dump(result1, f, indent=2, ensure_ascii=False)

        print(f"\n结果已保存到: {output_dir / 'mmc_case_topk_auto.json'}")

        # ========== 方式2：指定起止点 + Top-K路径 ==========
        print("\n\n[方式2] 指定起止点 + Top-5路径:")
        print("=" * 60)
        result2 = coordinator.process_top_k_with_specific_functions(
            mmc_error_log,
            start_func='dw_mci_pltfm_probe',
            end_func='dw_mci_execute_tuning',
            k=5
        )

        with open(output_dir / 'mmc_case_topk_specific.json', 'w', encoding='utf-8') as f:
            json.dump(result2, f, indent=2, ensure_ascii=False)

        print(f"\n结果已保存到: {output_dir / 'mmc_case_topk_specific.json'}")

        # ========== 方式3：使用call_line剪枝（示例） ==========
        print("\n\n[方式3] 指定起止点 + call_line剪枝 + Top-5路径:")
        print("=" * 60)
        print("注意: 这是一个演示，error_line=200 意味着只搜索第200行之前的调用")

        result3 = coordinator.process_top_k_with_specific_functions(
            mmc_error_log,
            start_func='dw_mci_pltfm_probe',
            end_func='dw_mci_execute_tuning',
            k=5,
            error_line=200  # 假设错误发生在第200行，只搜索该行之前的调用
        )

        with open(output_dir / 'mmc_case_topk_pruned.json', 'w', encoding='utf-8') as f:
            json.dump(result3, f, indent=2, ensure_ascii=False)

        print(f"\n结果已保存到: {output_dir / 'mmc_case_topk_pruned.json'}")

        # 显示对比
        print("\n\n" + "=" * 60)
        print("路径数量对比:")
        print("=" * 60)
        print(f"  方式1 (自动推断):     {result1.get('path_count', 0)} 条路径")
        print(f"  方式2 (指定起止点):   {result2.get('path_count', 0)} 条路径")
        print(f"  方式3 (call_line剪枝): {result3.get('path_count', 0)} 条路径")

    finally:
        coordinator.close()


def demo_topk_direct():
    """直接使用KG接口演示Top-K搜索"""
    from data.kg_interface import KnowledgeGraphInterface

    print_header("直接使用KG接口演示Top-K搜索")

    data_dir = "/data/xuao/code_kg_search/linux_test/data/mmc"
    if not os.path.exists(data_dir):
        data_dir = "/data/xuao/code_kg_search/linux_test/data"

    kg = KnowledgeGraphInterface(data_dir)

    try:
        # 测试Top-K路径搜索
        print("\n测试: 从 dw_mci_pltfm_probe 到 dw_mci_execute_tuning")
        print("=" * 60)

        paths = kg.find_top_k_call_paths_with_indirect(
            start='dw_mci_pltfm_probe',
            end='dw_mci_execute_tuning',
            max_depth=30,
            k=5,
            debug=True
        )

        print(f"\n找到 {len(paths)} 条路径:")
        for idx, path in enumerate(paths):
            print(f"\n路径 #{idx+1}:")
            print(f"  长度: {path['length']}")
            print(f"  间接调用: {path['indirect_count']}")
            print(f"  得分: {path['score']}")
            print(f"  路径: {' -> '.join(path['path'][:5])} ... {' -> '.join(path['path'][-3:])}")

    finally:
        kg.close()


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == '--direct':
        # 直接测试KG接口
        demo_topk_direct()
    else:
        # 完整流程测试
        run_mmc_case_topk()


if __name__ == "__main__":
    main()
