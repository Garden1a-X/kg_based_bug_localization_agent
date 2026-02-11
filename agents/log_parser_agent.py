"""
日志解析Agent
从错误日志中提取结构化信息
"""
import re
from typing import Dict, List
from agents.base_agent import BaseAgent


class LogParserAgent(BaseAgent):
    """日志解析Agent - 规则为主"""
    
    def __init__(self):
        super().__init__("LogParser")
        
        # 定义常见的错误模式
        self.error_patterns = {
            'error_message': r'(error|Error|ERROR)[:\s]+(.+?)(?:\n|$)',
            'error_code': r'error[:\s]+(-?\d+)',
            'function_name': r'([a-zA-Z_][a-zA-Z0-9_]+)\s*\(',
            'file_path': r'([/\w]+\.c)',
            'line_number': r':(\d+):',
        }
    
    def execute(self, log_text: str) -> Dict:
        """
        解析日志文本
        
        Args:
            log_text: 原始日志文本
            
        Returns:
            结构化的日志信息
        """
        self.log_start("解析错误日志")
        
        result = {
            'raw_log': log_text,
            'error_messages': self._extract_error_messages(log_text),
            'error_codes': self._extract_error_codes(log_text),
            'functions': self._extract_functions(log_text),
            'files': self._extract_files(log_text),
            'lines': self._extract_line_numbers(log_text)
        }
        
        self.log_success(f"提取到 {len(result['error_messages'])} 个错误消息")
        self.log_info(f"涉及函数: {result['functions']}")
        
        return result
    
    def _extract_error_messages(self, log_text: str) -> List[str]:
        """提取错误消息"""
        messages = []
        
        # 模式1: "error: xxx"
        pattern1 = re.findall(r'error[:\s]+(.+?)(?:\n|$)', log_text, re.IGNORECASE)
        messages.extend(pattern1)
        
        # 模式2: "failed: xxx"  
        pattern2 = re.findall(r'failed[:\s]+(.+?)(?:\n|$)', log_text, re.IGNORECASE)
        messages.extend(pattern2)
        
        # 模式3: "xxx whilst xxx"
        pattern3 = re.findall(r'(.+?whilst.+?)(?:\n|$)', log_text)
        messages.extend(pattern3)
        
        return list(set(messages))  # 去重
    
    def _extract_error_codes(self, log_text: str) -> List[int]:
        """提取错误码"""
        codes = re.findall(r'[-]?\d+', log_text)
        return [int(c) for c in codes if c.startswith('-') or int(c) > 0]
    
    def _extract_functions(self, log_text: str) -> List[str]:
        """提取函数名"""
        # 匹配 C 函数名模式
        functions = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]+)\s*\(', log_text)
        return list(set(functions))
    
    def _extract_files(self, log_text: str) -> List[str]:
        """提取文件路径"""
        files = re.findall(r'([/\w]+\.c)', log_text)
        return list(set(files))
    
    def _extract_line_numbers(self, log_text: str) -> List[int]:
        """提取行号"""
        lines = re.findall(r':(\d+):', log_text)
        return [int(l) for l in lines]
    
    def parse_mmc_log(self, log_text: str) -> Dict:
        """
        专门针对MMC日志的解析（甲方案例）

        Args:
            log_text: MMC错误日志

        Returns:
            解析结果，包含推断的起点和终点
        """
        basic_result = self.execute(log_text)

        # MMC特定的解析逻辑
        result = basic_result.copy()

        # ====================================================================
        # Mock: 从简单日志推断关键函数
        # TODO: 未来替换为真实的LLM推断或更复杂的规则
        # ====================================================================
        key_functions = []

        # 规则1: "ALL phases bad!" -> dw_mci_hi3660_execute_tuning
        if "ALL phases bad" in log_text or "phases bad" in log_text:
            key_functions.append('dw_mci_hi3660_execute_tuning')

        # 规则2: "tuning execution failed" -> mmc_execute_tuning
        if "tuning execution failed" in log_text:
            key_functions.append('mmc_execute_tuning')

        # 规则3: "whilst initialising MMC card" -> mmc_attach_mmc
        if "whilst initialising MMC card" in log_text or "initialising MMC" in log_text:
            key_functions.append('mmc_attach_mmc')

        # 将识别的关键函数添加到结果中
        if key_functions:
            result['key_functions'] = key_functions
            self.log_info(f"从日志识别出 {len(key_functions)} 个关键函数: {key_functions}")

        # 推断入口函数（通常是 probe 函数）
        entry_candidates = [f for f in result['functions'] if 'probe' in f.lower()]
        if entry_candidates:
            result['inferred_entry'] = entry_candidates[0]
        else:
            result['inferred_entry'] = 'dw_mci_pltfm_probe'  # 默认

        # 推断错误点（通常包含execute, tuning等关键词）
        error_candidates = [f for f in result['functions']
                          if any(kw in f.lower() for kw in ['execute', 'tuning', 'init'])]
        if error_candidates:
            result['inferred_error_point'] = error_candidates[0]
        else:
            # 从关键函数推断（取最深层的）
            if key_functions:
                result['inferred_error_point'] = key_functions[0]  # 第一个通常是最深层的
            elif 'tuning' in log_text.lower():
                result['inferred_error_point'] = 'dw_mci_execute_tuning'

        return result
