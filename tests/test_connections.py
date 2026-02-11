"""
测试连接脚本
验证数据文件和Anthropic API连接
"""
import os
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

console = Console()

# 加载环境变量
load_dotenv()


def test_data_files():
    """测试数据文件"""
    console.print("\n[bold cyan]测试数据文件...[/bold cyan]")

    try:
        data_dir = os.getenv('KG_DATA_DIR', '/data/xuao/code_kg_search/linux_test/data')
        data_path = Path(data_dir)

        console.print(f"  数据目录: {data_dir}")

        if not data_path.exists():
            console.print(f"[red]✗[/red] 数据目录不存在")
            return False

        # 检查合并格式文件
        entity_file = data_path / 'temp_en.json'
        relation_file = data_path / 'relations.json'

        has_merged = entity_file.exists() and relation_file.exists()

        if has_merged:
            console.print("[green]✓[/green] 检测到合并格式数据文件")

            # 读取并统计实体
            with open(entity_file, 'r', encoding='utf-8') as f:
                entities = json.load(f)

            # 读取并统计关系
            with open(relation_file, 'r', encoding='utf-8') as f:
                relations = json.load(f)

            # 显示统计信息
            table = Table(title="数据统计")
            table.add_column("类型", style="cyan")
            table.add_column("数量", style="green", justify="right")

            if isinstance(entities, dict):
                for entity_type, entity_list in entities.items():
                    if isinstance(entity_list, list):
                        table.add_row(f"实体-{entity_type}", str(len(entity_list)))

            if isinstance(relations, dict):
                for rel_type, rel_list in relations.items():
                    if isinstance(rel_list, list):
                        table.add_row(f"关系-{rel_type}", str(len(rel_list)))

            console.print(table)
            return True

        # 检查分散格式文件
        else:
            console.print("[yellow]⚠[/yellow] 未找到合并格式文件，检查分散格式...")

            entity_files = list(data_path.glob('entity_*.json'))
            relation_files = list(data_path.glob('relation_*.json'))

            if entity_files or relation_files:
                console.print(f"[green]✓[/green] 检测到分散格式数据文件")
                console.print(f"  实体文件数: {len(entity_files)}")
                console.print(f"  关系文件数: {len(relation_files)}")
                return True
            else:
                console.print("[red]✗[/red] 未找到任何数据文件")
                return False

    except Exception as e:
        console.print(f"[red]✗[/red] 数据文件检查失败: {e}")
        return False


def test_kg_interface():
    """测试知识图谱接口"""
    console.print("\n[bold cyan]测试知识图谱接口...[/bold cyan]")

    try:
        from data.kg_interface import KnowledgeGraphInterface

        # 创建接口
        data_dir = os.getenv('KG_DATA_DIR', '/data/xuao/code_kg_search/linux_test/data')
        kg = KnowledgeGraphInterface(data_dir)

        # 获取统计信息
        stats = kg.get_database_stats()

        console.print("[green]✓[/green] 知识图谱接口加载成功")

        # 显示统计
        table = Table(title="图谱统计")
        table.add_column("类型", style="cyan")
        table.add_column("数量", style="green", justify="right")

        for key, value in stats.items():
            table.add_row(key, str(value))

        console.print(table)

        kg.close()
        return True

    except Exception as e:
        console.print(f"[red]✗[/red] 知识图谱接口加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_anthropic_connection():
    """测试Anthropic API连接"""
    console.print("\n[bold cyan]测试Anthropic API连接...[/bold cyan]")

    try:
        api_key = os.getenv('ANTHROPIC_API_KEY')

        if not api_key:
            console.print("[yellow]⚠[/yellow] 未配置ANTHROPIC_API_KEY")
            console.print("  LLM功能将不可用，但不影响基于规则的功能")
            return True  # 不算错误，只是功能受限

        try:
            import anthropic
        except ImportError:
            console.print("[red]✗[/red] 未安装anthropic库")
            console.print("  运行: pip install anthropic")
            return False

        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": "Hi, 测试连接"}]
        )

        if response.content:
            console.print("[green]✓[/green] Anthropic API连接成功")
            console.print(f"  模型: claude-sonnet-4-20250514")
            console.print(f"  响应: {response.content[0].text[:50]}...")
            return True
        else:
            console.print("[red]✗[/red] API返回为空")
            return False

    except Exception as e:
        console.print(f"[red]✗[/red] Anthropic API连接失败: {e}")
        return False


def test_project_structure():
    """测试项目结构"""
    console.print("\n[bold cyan]检查项目结构...[/bold cyan]")

    required_dirs = ['config', 'data', 'agents', 'coordinator', 'utils', 'tests']
    all_exist = True

    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            console.print(f"[green]✓[/green] {dir_name}/ 存在")
        else:
            console.print(f"[red]✗[/red] {dir_name}/ 不存在")
            all_exist = False

    return all_exist


def main():
    """运行所有测试"""
    console.print("[bold green]===== 环境检查 =====[/bold green]")

    results = {
        '项目结构': test_project_structure(),
        '数据文件': test_data_files(),
        '知识图谱接口': test_kg_interface(),
        'Anthropic API': test_anthropic_connection()
    }

    console.print("\n[bold cyan]===== 检查结果 =====[/bold cyan]")
    for name, result in results.items():
        status = "[green]✓[/green]" if result else "[red]✗[/red]"
        console.print(f"{status} {name}")

    # 判断是否可以运行
    can_run = results['项目结构'] and results['数据文件'] and results['知识图谱接口']

    if can_run:
        console.print("\n[bold green]✓ 环境配置正确，可以运行框架[/bold green]")
        if not results['Anthropic API']:
            console.print("[yellow]⚠ LLM功能将受限（仅影响第3层兜底）[/yellow]")
    else:
        console.print("\n[bold red]✗ 环境配置有问题，请先修复[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
