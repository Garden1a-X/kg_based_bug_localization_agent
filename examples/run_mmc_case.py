"""
运行甲方MMC案例
演示框架的完整功能
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from coordinator.master_coordinator import MasterCoordinator
from llm.openai_client import OpenAIClient
from utils.logger import setup_logger, print_header
import json

# 配置日志
setup_logger()


def run_mmc_case():
    """运行甲方MMC案例"""

    # 甲方提供的错误日志（3行简单日志）
    mmc_error_log = """
ALL phases bad!
mmc0: tuning execution failed: -1
mmc0: error -1 whilst initialising MMC card
    """

    print_header("运行甲方MMC案例")

    # 指定数据目录
    data_dir = "/data/xuao/code_kg_search/linux_test/data"

    # 创建协调器（不启用LLM）
    # 注意: LLM源码分析功能已集成但暂未在主流程启用
    # 可以通过传入 llm_client 参数启用
    coordinator = MasterCoordinator(data_dir=data_dir, llm_client=None)
    
    try:
        # 方式1：自动推断起点和终点
        print("\n[方式1] 自动推断起点和终点:")
        print("=" * 60)
        result1 = coordinator.process(mmc_error_log)
        
        # 保存结果
        output_dir = project_root / 'output'
        output_dir.mkdir(exist_ok=True)
        
        with open(output_dir / 'mmc_case_auto.json', 'w', encoding='utf-8') as f:
            json.dump(result1, f, indent=2, ensure_ascii=False)
        
        print(f"\n结果已保存到: {output_dir / 'mmc_case_auto.json'}")
        
        # 方式2：指定起点和终点
        print("\n\n[方式2] 指定起点和终点:")
        print("=" * 60)
        result2 = coordinator.process_with_specific_functions(
            mmc_error_log,
            start_func='dw_mci_pltfm_probe',
            end_func='dw_mci_execute_tuning'
        )
        
        with open(output_dir / 'mmc_case_specific.json', 'w', encoding='utf-8') as f:
            json.dump(result2, f, indent=2, ensure_ascii=False)
        
        print(f"\n结果已保存到: {output_dir / 'mmc_case_specific.json'}")
        
        # 显示调用链
        if result2['success']:
            print("\n[bold green]✓ 成功找到完整调用链[/bold green]")
            print("\n完整路径:")
            for i, func in enumerate(result2['chain']['path']):
                print(f"  {i+1}. {func}")
        else:
            print("\n[bold yellow]⚠ 找到部分调用链，有未修复的断点[/bold yellow]")
        
    finally:
        coordinator.close()


def run_custom_case(log_file: str):
    """
    运行自定义案例

    Args:
        log_file: 日志文件路径
    """
    print_header(f"运行自定义案例: {log_file}")

    # 读取日志
    with open(log_file, 'r', encoding='utf-8') as f:
        log_text = f.read()

    # 创建 LLM 客户端（可选）
    llm_client = create_llm_client()

    # 创建协调器
    data_dir = "/data/xuao/code_kg_search/linux_test/data"
    coordinator = MasterCoordinator(data_dir=data_dir, llm_client=llm_client)
    
    try:
        result = coordinator.process(log_text)
        
        # 保存结果
        output_file = Path(log_file).stem + '_result.json'
        output_dir = project_root / 'output'
        output_dir.mkdir(exist_ok=True)
        
        with open(output_dir / output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n结果已保存到: {output_dir / output_file}")
        
    finally:
        coordinator.close()


def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 运行自定义案例
        log_file = sys.argv[1]
        if not os.path.exists(log_file):
            print(f"错误: 文件不存在 {log_file}")
            sys.exit(1)
        run_custom_case(log_file)
    else:
        # 运行甲方MMC案例
        run_mmc_case()


if __name__ == "__main__":
    main()
