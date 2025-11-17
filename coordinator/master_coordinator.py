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

    def __init__(self, data_dir: str = None, llm_client=None, enable_llm_detection: bool = False, enable_llm_log_analysis: bool = False):
        """
        初始化协调器

        Args:
            data_dir: 数据文件目录
            llm_client: LLM客户端（可选）
            enable_llm_detection: 是否启用LLM辅助间接调用检测（预处理模式）
            enable_llm_log_analysis: 是否启用LLM辅助日志分析
        """
        logger.info("初始化主协调器...")

        # 创建知识图谱接口
        self.kg = KnowledgeGraphInterface(data_dir, enable_llm_detection=enable_llm_detection)

        # 如果启用LLM检测，执行预处理
        if enable_llm_detection:
            logger.info("LLM间接调用检测已启用，开始预处理...")
            self.kg.preprocess_llm_indirect_calls()

        # 创建各个Agent
        self.log_parser = LogParserAgent(enable_llm=enable_llm_log_analysis)
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

        # 只显示一次函数列表（优先显示 functions，如果 key_functions 与之不同才显示）
        functions = parsed.get('functions', [])
        key_functions = parsed.get('key_functions', [])

        if functions:
            table.add_row("涉及函数", ", ".join(functions))

        # 只有在 key_functions 存在且与 functions 不同时才显示
        if key_functions and key_functions != functions:
            table.add_row("关键函数", ", ".join(key_functions))

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

    def process_top_k(
        self,
        log_text: str,
        k: int = 5,
        error_line: int = None
    ) -> Dict:
        """
        处理错误日志，返回Top-K条调用链

        Args:
            log_text: 错误日志文本
            k: 返回路径数量上限
            error_line: 已废弃（保留用于兼容性，不再用于剪枝）

        Returns:
            包含多条路径的分析结果
        """
        print_header(f"Bug定位分析流程 (Top-{k}路径)")

        # 第1步：日志解析
        print_step(1, 4, "解析错误日志")
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

        # 第3步：追踪Top-K条调用链
        print_step(3, 4, "追踪Top-K条调用链")
        paths = self.chain_tracer.execute_top_k(
            entities['start_entity'],
            entities['end_entity'],
            intermediate_entities=entities.get('intermediate_entities', []),
            k=k,
            error_line=error_line
        )
        self._display_multiple_chains(paths)

        # 第4步：生成报告
        print_step(4, 4, "生成分析报告")
        report = self._generate_multi_path_report(parsed_log, entities, paths)

        print_success(f"分析完成！找到 {len(paths)} 条路径")

        return report

    def process_top_k_with_specific_functions(
        self,
        log_text: str,
        start_func: str,
        end_func: str,
        intermediate_funcs: list = None,
        k: int = 5,
        error_line: int = None
    ) -> Dict:
        """
        使用指定的起点、终点和中间节点，返回Top-K条调用链

        Args:
            log_text: 错误日志文本（可选，仅用于报告）
            start_func: 起点函数名
            end_func: 终点函数名
            intermediate_funcs: 中间节点函数名列表（可选）
            k: 返回路径数量上限
            error_line: 已废弃（保留用于兼容性，不再用于剪枝）

        Returns:
            包含多条路径的分析结果
        """
        print_header(f"Bug定位分析流程（指定起止点，Top-{k}路径）")

        # 第1步：日志解析（仅用于报告）
        print_step(1, 3, "解析错误日志")
        parsed_log = self.log_parser.execute(log_text)

        # 第2步：定位指定函数
        print_step(2, 3, "定位指定函数")
        entities = self.entity_locator.locate_specific(
            start_func,
            end_func,
            intermediate_names=intermediate_funcs
        )
        self._display_entities(entities)

        if not entities['start_entity'] or not entities['end_entity']:
            print_error("无法定位指定的起点或终点")
            return {
                'success': False,
                'error': '无法定位指定函数'
            }

        # 第3步：追踪Top-K条调用链
        print_step(3, 3, "追踪Top-K条调用链")
        paths = self.chain_tracer.execute_top_k(
            entities['start_entity'],
            entities['end_entity'],
            intermediate_entities=entities.get('intermediate_entities', []),
            k=k,
            error_line=error_line
        )
        self._display_multiple_chains(paths)

        # 生成报告
        report = self._generate_multi_path_report(parsed_log, entities, paths)
        print_success(f"分析完成！找到 {len(paths)} 条路径")

        return report

    def _display_multiple_chains(self, paths: list):
        """显示多条调用链"""
        if not paths:
            console.print("[yellow]未找到路径[/yellow]")
            return

        console.print(f"[bold cyan]找到 {len(paths)} 条路径:[/bold cyan]\n")

        for idx, path_result in enumerate(paths):
            path = path_result['path']
            breaks = path_result['breaks']
            score = path_result.get('score', 0)
            indirect_count = path_result.get('indirect_count', 0)
            avg_call_line = path_result.get('avg_call_line', 0)
            matched_key_functions = path_result.get('matched_key_functions', [])
            missed_key_functions = path_result.get('missed_key_functions', [])

            # 构建关键函数集合（用于快速查找）
            key_function_set = set(matched_key_functions + missed_key_functions)

            # 路径标题（包含关键函数覆盖率）
            title = f"[bold green]路径 #{idx+1}[/bold green] " \
                   f"(长度={len(path)}, 间接调用={indirect_count}, " \
                   f"平均行号={avg_call_line:.1f}, 得分={score:.2f}"
            if key_function_set:
                coverage = len(matched_key_functions) / len(key_function_set) * 100
                title += f", 关键函数覆盖率={coverage:.0f}%"
            title += ")"
            console.print(title)

            # 显示路径
            for i, func in enumerate(path):
                # 检查是否是断点修复的位置
                is_bridge = any(b['position'] == i-1 and b['fixed']
                              for b in breaks)

                # 检查是否是关键函数
                is_key_function = func in key_function_set

                # 显示 call_line 信息
                call_line_info = ""
                if 'call_lines' in path_result and i > 0:
                    call_line = path_result['call_lines'][i-1]
                    if call_line:
                        call_line_info = f" [dim](line {call_line})[/dim]"

                if is_bridge:
                    # 找到桥接类型
                    bridge_type = "桥接"
                    for b in breaks:
                        if b['position'] == i-1 and b['fixed']:
                            bridge_info = b.get('bridge', {})
                            bridge_type = bridge_info.get('bridge_type', '桥接')
                            break
                    # 间接调用用黄色，如果同时是关键函数也标注
                    if is_key_function:
                        console.print(f"  {i}. [yellow]{func}[/yellow] ({bridge_type}) [cyan]✓关键函数[/cyan]{call_line_info}")
                    else:
                        console.print(f"  {i}. [yellow]{func}[/yellow] ({bridge_type}){call_line_info}")
                else:
                    # 关键函数用青色高亮
                    if is_key_function:
                        console.print(f"  {i}. [cyan]{func} ✓[/cyan]{call_line_info}")
                    else:
                        console.print(f"  {i}. {func}{call_line_info}")

            # 显示未经过的关键函数
            if missed_key_functions:
                console.print(f"  [dim]⚠ 未经过的关键函数: {', '.join(missed_key_functions)}[/dim]")

            console.print()

    def _generate_multi_path_report(self, parsed_log: Dict, entities: Dict,
                                    paths: list) -> Dict:
        """生成多路径分析报告"""
        if not paths:
            return {
                'success': False,
                'parsed_log': parsed_log,
                'entities': entities,
                'paths': [],
                'error': '未找到路径'
            }

        report = {
            'success': True,
            'parsed_log': parsed_log,
            'entities': entities,
            'paths': paths,
            'path_count': len(paths),
            'best_path': paths[0] if paths else None  # 得分最高的路径
        }

        # 显示总结
        self._display_multi_path_summary(report)

        return report

    def _display_multi_path_summary(self, report: Dict):
        """显示多路径总结"""
        paths = report['paths']
        if not paths:
            return

        # 统计信息
        total_paths = len(paths)
        min_length = min(len(p['path']) for p in paths)
        max_length = max(len(p['path']) for p in paths)
        avg_length = sum(len(p['path']) for p in paths) / total_paths

        min_indirect = min(p.get('indirect_count', 0) for p in paths)
        max_indirect = max(p.get('indirect_count', 0) for p in paths)

        summary = f"""
找到路径数: {total_paths}
路径长度: {min_length} - {max_length} (平均 {avg_length:.1f})
间接调用: {min_indirect} - {max_indirect}
最佳路径: 路径 #1 (得分={paths[0].get('score', 0)})
        """

        print_panel("多路径分析总结", summary.strip(), style="green")
