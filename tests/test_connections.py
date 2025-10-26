"""
测试连接脚本
验证Neo4j和Anthropic API连接
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from neo4j import GraphDatabase
from rich.console import Console

console = Console()

# 加载环境变量
load_dotenv()


def test_neo4j_connection():
    """测试Neo4j连接"""
    console.print("\n[bold cyan]测试Neo4j连接...[/bold cyan]")
    
    try:
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD')
        
        if not password:
            console.print("[red]✗[/red] 未配置NEO4J_PASSWORD")
            return False
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            result = session.run("RETURN 1 as num")
            num = result.single()['num']
            
            if num == 1:
                console.print(f"[green]✓[/green] Neo4j连接成功")
                console.print(f"  URI: {uri}")
                
                # 获取数据库统计
                stats_query = """
                MATCH (n) 
                WITH labels(n) as labels, count(*) as count
                UNWIND labels as label
                RETURN label, sum(count) as total
                ORDER BY total DESC
                LIMIT 5
                """
                stats = session.run(stats_query)
                console.print("\n  数据库统计（前5类实体）:")
                for record in stats:
                    console.print(f"    {record['label']}: {record['total']}")
                
                driver.close()
                return True
            else:
                console.print("[red]✗[/red] Neo4j返回异常")
                return False
                
    except Exception as e:
        console.print(f"[red]✗[/red] Neo4j连接失败: {e}")
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
        'Neo4j连接': test_neo4j_connection(),
        'Anthropic API': test_anthropic_connection()
    }
    
    console.print("\n[bold cyan]===== 检查结果 =====[/bold cyan]")
    for name, result in results.items():
        status = "[green]✓[/green]" if result else "[red]✗[/red]"
        console.print(f"{status} {name}")
    
    # 判断是否可以运行
    can_run = results['项目结构'] and results['Neo4j连接']
    
    if can_run:
        console.print("\n[bold green]✓ 环境配置正确，可以运行框架[/bold green]")
        if not results['Anthropic API']:
            console.print("[yellow]⚠ LLM功能将受限（仅影响第2层兜底）[/yellow]")
    else:
        console.print("\n[bold red]✗ 环境配置有问题，请先修复[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
