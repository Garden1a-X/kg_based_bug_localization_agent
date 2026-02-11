"""
主协调器
协调所有Agent完成Bug定位任务
"""
from typing import Dict
from data.kg_interface import KnowledgeGraphInterface
from agents.log_parser_agent import LogParserAgent
from agents.entity_locator_agent import EntityLocatorAgent
from agents.chain_tracer_agent import CallChainTracerAgent
from utils.logger import logger, print_header, print_step, print_success, print_error, print_panel
from rich.console import Console
from rich.table import Table

console = Console()


class MasterCoordinator:
    """主协调器"""

    def __init__(self, data_dir: str = None, llm_client=None):
        """
        初始化协调器

        Args:
            data_dir: 数据文件目录
            llm_client: LLM客户端（可选）
        """
        logger.info("初始化主协调器...")

        # 创建知识图谱接口
        self.kg = KnowledgeGraphInterface(data_dir)

        # 创建各个Agent
        self.log_parser = LogParserAgent()
        self.entity_locator = EntityLocatorAgent(self.kg)
        self.chain_tracer = CallChainTracerAgent(self.kg, llm_client)

        logger.success("协调器初始化完成")
    
    def process(self, log_text: str) -> Dict:
        """
        处理错误日志，进行bug定位
        
        Args:
            log_text: 错误日志文本
            
        Returns:
            分析结果
        """
        print_header("Bug定位分析流程")
        
        # 第1步：日志解析
        print_step(1, 4, "解析错误日志")
        # 检测是否是 MMC 日志
        if 'mmc' in log_text.lower() or 'tuning' in log_text.lower():
            parsed_log = self.log_parser.parse_mmc_log(log_text)
        else:
            parsed_log = self.log_parser.execute(log_text)
        self._display_parsed_log(parsed_log)
        
        # 第2步：实体定位
        print_step(2, 4, "在图谱中定位实体")
        entities = self.entity_locator.execute(parsed_log)
        self._display_entities(entities)
        
        # 检查是否找到起点和终点
        if not entities['start_entity'] or not entities['end_entity']:
            print_error("无法定位起点或终点，分析终止")
            return {
                'success': False,
                'parsed_log': parsed_log,
                'entities': entities,
                'error': '无法定位起点或终点'
            }
        
        # 第3步：调用链追踪
        print_step(3, 4, "追踪调用链")
        chain_result = self.chain_tracer.execute(
            entities['start_entity'],
            entities['end_entity']
        )
        self._display_chain(chain_result)
        
        # 第4步：生成报告
        print_step(4, 4, "生成分析报告")
        report = self._generate_report(parsed_log, entities, chain_result)
        
        print_success("分析完成！")
        
        return report
    
    def process_with_specific_functions(self, log_text: str, 
                                       start_func: str, end_func: str) -> Dict:
        """
        处理错误日志，使用指定的起点和终点
        
        Args:
            log_text: 错误日志文本
            start_func: 起点函数名
            end_func: 终点函数名
            
        Returns:
            分析结果
        """
        print_header("Bug定位分析流程（指定起止点）")
        
        # 第1步：日志解析
        print_step(1, 3, "解析错误日志")
        parsed_log = self.log_parser.execute(log_text)
        
        # 第2步：定位指定函数
        print_step(2, 3, "定位指定函数")
        entities = self.entity_locator.locate_specific(start_func, end_func)
        self._display_entities(entities)
        
        if not entities['start_entity'] or not entities['end_entity']:
            print_error("无法定位指定的起点或终点")
            return {
                'success': False,
                'error': '无法定位指定函数'
            }
        
        # 第3步：调用链追踪
        print_step(3, 3, "追踪调用链")
        chain_result = self.chain_tracer.execute(
            entities['start_entity'],
            entities['end_entity']
        )
        self._display_chain(chain_result)
        
        # 生成报告
        report = self._generate_report(parsed_log, entities, chain_result)
        print_success("分析完成！")
        
        return report
    
    def _generate_report(self, parsed_log: Dict, entities: Dict, 
                        chain_result: Dict) -> Dict:
        """生成分析报告"""
        report = {
            'success': chain_result.get('success', False),
            'parsed_log': parsed_log,
            'entities': entities,
            'chain': {
                'path': chain_result['path'],
                'length': len(chain_result['path']),
                'breaks': chain_result['breaks'],
                'stats': chain_result['stats']
            }
        }
        
        # 显示报告
        self._display_report(report)
        
        return report
    
    def _display_parsed_log(self, parsed: Dict):
        """显示日志解析结果"""
        table = Table(title="日志解析结果")
        table.add_column("项目", style="cyan")
        table.add_column("内容", style="green")

        table.add_row("错误消息", str(parsed.get('error_messages', [])))
        table.add_row("错误码", str(parsed.get('error_codes', [])))
        table.add_row("涉及函数", ", ".join(parsed.get('functions', [])))

        if 'key_functions' in parsed:
            table.add_row("关键函数", ", ".join(parsed['key_functions']))

        if 'inferred_entry' in parsed:
            table.add_row("推断入口", parsed['inferred_entry'])
        if 'inferred_error_point' in parsed:
            table.add_row("推断错误点", parsed['inferred_error_point'])

        console.print(table)
        console.print()
    
    def _display_entities(self, entities: Dict):
        """显示实体定位结果"""
        table = Table(title="实体定位结果")
        table.add_column("实体", style="cyan")
        table.add_column("函数名", style="green")
        table.add_column("文件", style="yellow")
        
        if entities.get('start_entity'):
            table.add_row("起点", 
                         entities['start_entity']['name'],
                         entities['start_entity'].get('file', 'N/A'))
        
        if entities.get('end_entity'):
            table.add_row("终点",
                         entities['end_entity']['name'],
                         entities['end_entity'].get('file', 'N/A'))
        
        console.print(table)
        console.print()
    
    def _display_chain(self, chain_result: Dict):
        """显示调用链结果"""
        path = chain_result['path']
        breaks = chain_result['breaks']
        stats = chain_result['stats']
        
        # 显示路径
        console.print("[bold cyan]调用路径:[/bold cyan]")
        for i, func in enumerate(path):
            # 检查是否是断点修复的位置
            is_bridge = any(b['position'] == i-1 and b['fixed'] 
                          for b in breaks)
            
            if is_bridge:
                console.print(f"  {i}. [yellow]{func}[/yellow] (桥接)")
            else:
                console.print(f"  {i}. {func}")
        console.print()
        
        # 显示断点统计
        if stats['total_breaks'] > 0:
            console.print("[bold cyan]断点修复统计:[/bold cyan]")
            console.print(f"  总断点数: {stats['total_breaks']}")
            console.print(f"  规则修复: {stats['fixed_by_rules']}")
            console.print(f"  LLM源码分析修复: {stats.get('fixed_by_source_analysis', 0)} ✨")
            console.print(f"  LLM推理修复: {stats['fixed_by_llm']}")
            console.print(f"  未修复: {stats['unfixed']}")
            console.print()
        
        # 显示断点详情
        if breaks:
            table = Table(title="断点详情")
            table.add_column("位置", style="cyan")
            table.add_column("从", style="green")
            table.add_column("到", style="green")
            table.add_column("状态", style="yellow")
            table.add_column("方法", style="magenta")
            
            for b in breaks:
                status = "✓ 已修复" if b['fixed'] else "✗ 未修复"
                method = b.get('method', 'N/A')
                
                table.add_row(
                    str(b['position']),
                    b['from'],
                    b['to'],
                    status,
                    method
                )
            
            console.print(table)
            console.print()
    
    def _display_report(self, report: Dict):
        """显示最终报告"""
        success = report['success']
        chain = report['chain']
        stats = chain['stats']

        # 计算已修复数量
        fixed_count = (stats['fixed_by_rules'] +
                      stats.get('fixed_by_source_analysis', 0) +
                      stats['fixed_by_llm'])

        # 创建总结面板
        summary = f"""
状态: {'✓ 成功' if success else '✗ 部分成功'}
调用链长度: {chain['length']}
总断点数: {stats['total_breaks']}
已修复: {fixed_count}
  - 规则修复: {stats['fixed_by_rules']}
  - LLM源码分析: {stats.get('fixed_by_source_analysis', 0)} ✨
  - LLM推理: {stats['fixed_by_llm']}
未修复: {stats['unfixed']}
        """

        print_panel("分析总结", summary.strip(),
                   style="green" if success else "yellow")
    
    def close(self):
        """关闭协调器"""
        self.kg.close()
        logger.info("协调器已关闭")
