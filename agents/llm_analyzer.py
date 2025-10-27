#!/usr/bin/env python3
"""
LLM分析器：使用大语言模型分析bug日志，提取可能相关的函数名
"""

import json
from typing import Dict, List, Optional
from openai import OpenAI


class LLMAnalyzer:
    """使用LLM分析bug日志，提取可能的函数名"""

    def __init__(self, api_key: str = "", base_url: str = "http://10.12.208.86:8502"):
        """
        初始化LLM分析器

        Args:
            api_key: OpenAI API密钥
            base_url: API服务地址
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = "gpt-4o-mini"  # 使用便宜的模型
        self.timeout = 180  # 超时时间（秒），考虑到冷启动可能需要较长时间

    def analyze_bug_log(self, bug_log: str, context: Optional[str] = None) -> Dict[str, List[str]]:
        """
        分析bug日志，提取可能相关的函数名

        Args:
            bug_log: bug日志内容
            context: 可选的上下文信息（如代码库信息、bug描述等）

        Returns:
            {
                "entry_functions": ["func1", "func2"],  # 可能的起始函数
                "intermediate_functions": ["func3"],     # 可能的中间函数
                "error_functions": ["func4", "func5"]    # 可能的错误发生函数
            }
        """
        prompt = self._build_log_analysis_prompt(bug_log, context)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert system for analyzing kernel bug logs and identifying relevant functions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 较低温度以获得更确定的输出
                max_tokens=1000,
                timeout=self.timeout
            )

            # 提取回复内容
            content = response.choices[0].message.content.strip()

            # 解析JSON输出
            result = self._parse_llm_output(content)

            return result

        except Exception as e:
            print(f"LLM分析失败: {e}")
            return {
                "entry_functions": [],
                "intermediate_functions": [],
                "error_functions": []
            }

    def _build_log_analysis_prompt(self, bug_log: str, context: Optional[str] = None) -> str:
        """构建日志分析的prompt"""
        prompt = f"""Analyze the following Linux kernel bug log and identify the relevant function names.

Bug Log:
```
{bug_log}
```
"""

        if context:
            prompt += f"""
Additional Context:
{context}
"""

        prompt += """
Based on this log, identify:
1. **Entry Functions**: Functions that likely serve as entry points where the problematic execution path starts (e.g., driver probe functions, system call handlers, interrupt handlers)
2. **Intermediate Functions**: Functions that are likely called during the execution path (mentioned in stack trace or log messages)
3. **Error Functions**: Functions where the error actually occurs or is reported (e.g., functions that print error messages, trigger warnings, or cause crashes)

Please provide your analysis in the following JSON format:
```json
{
  "entry_functions": ["function_name1", "function_name2"],
  "intermediate_functions": ["function_name3", "function_name4"],
  "error_functions": ["function_name5", "function_name6"],
  "reasoning": "Brief explanation of your analysis"
}
```

Important:
- Only include actual function names (not macros or variable names)
- Prioritize functions explicitly mentioned in the log
- For entry functions, consider common kernel entry points (probe, init, open, etc.)
- Include variations of function names if uncertain (e.g., with/without prefixes)
- Limit to 5-10 most relevant functions per category
"""

        return prompt

    def _parse_llm_output(self, content: str) -> Dict[str, List[str]]:
        """解析LLM的JSON输出"""
        try:
            # 尝试提取JSON代码块
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                json_str = content

            # 解析JSON
            data = json.loads(json_str)

            # 验证必需字段
            result = {
                "entry_functions": data.get("entry_functions", []),
                "intermediate_functions": data.get("intermediate_functions", []),
                "error_functions": data.get("error_functions", []),
                "reasoning": data.get("reasoning", "")
            }

            return result

        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"LLM输出: {content}")

            # 回退：尝试简单的文本提取
            return self._fallback_parse(content)

    def _fallback_parse(self, content: str) -> Dict[str, List[str]]:
        """如果JSON解析失败，使用简单的文本提取"""
        result = {
            "entry_functions": [],
            "intermediate_functions": [],
            "error_functions": [],
            "reasoning": content
        }

        # 简单的启发式提取：查找可能的函数名（以字母或下划线开头，包含字母数字下划线）
        import re
        # 查找常见的函数名模式
        function_pattern = r'\b[a-z_][a-z0-9_]{2,}\b'
        matches = re.findall(function_pattern, content.lower())

        # 去重
        unique_matches = list(dict.fromkeys(matches))[:10]

        # 简单分配到error_functions（因为最可能有用）
        result["error_functions"] = unique_matches

        return result

    def suggest_breakpoints(
        self,
        start_function: str,
        end_function: str,
        knowledge: Optional[str] = None
    ) -> List[str]:
        """
        基于知识建议断点函数，用于连接起始和结束函数

        Args:
            start_function: 起始函数名
            end_function: 结束函数名
            knowledge: 可选的领域知识（如已知的调用模式、子系统信息等）

        Returns:
            建议的中间断点函数名列表
        """
        prompt = self._build_breakpoint_suggestion_prompt(
            start_function, end_function, knowledge
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert in Linux kernel architecture and function call chains."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=800,
                timeout=self.timeout
            )

            content = response.choices[0].message.content.strip()
            result = self._parse_breakpoint_output(content)

            return result

        except Exception as e:
            print(f"LLM断点建议失败: {e}")
            return []

    def _build_breakpoint_suggestion_prompt(
        self,
        start_function: str,
        end_function: str,
        knowledge: Optional[str] = None
    ) -> str:
        """构建断点建议的prompt"""
        prompt = f"""Given a Linux kernel call chain from "{start_function}" to "{end_function}", suggest intermediate functions that are likely to be called.

Start Function: {start_function}
End Function: {end_function}
"""

        if knowledge:
            prompt += f"""
Domain Knowledge:
{knowledge}
"""

        prompt += """
Please suggest 3-8 intermediate functions that are likely to be in the call path, ordered from most likely to least likely.

Provide your suggestions in the following JSON format:
```json
{
  "breakpoint_functions": [
    {"function": "function_name1", "reason": "why this function is likely in the path"},
    {"function": "function_name2", "reason": "..."}
  ]
}
```

Consider:
- Common kernel subsystem patterns (e.g., driver probe -> resource allocation -> registration)
- Function naming conventions (similar prefixes often indicate related functions)
- Typical call hierarchies in the relevant subsystem
"""

        return prompt

    def _parse_breakpoint_output(self, content: str) -> List[str]:
        """解析断点建议输出"""
        try:
            # 提取JSON
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                json_str = content

            data = json.loads(json_str)

            # 提取函数名
            breakpoints = []
            for item in data.get("breakpoint_functions", []):
                if isinstance(item, dict) and "function" in item:
                    breakpoints.append(item["function"])
                elif isinstance(item, str):
                    breakpoints.append(item)

            return breakpoints

        except Exception as e:
            print(f"断点输出解析失败: {e}")
            return []


# 便捷函数
def analyze_log_with_llm(bug_log: str, api_key: str = "", base_url: str = "http://10.12.208.86:8502") -> Dict[str, List[str]]:
    """便捷函数：使用LLM分析bug日志"""
    analyzer = LLMAnalyzer(api_key=api_key, base_url=base_url)
    return analyzer.analyze_bug_log(bug_log)


def suggest_breakpoints_with_llm(
    start_func: str,
    end_func: str,
    api_key: str = "",
    base_url: str = "http://10.12.208.86:8502"
) -> List[str]:
    """便捷函数：使用LLM建议断点"""
    analyzer = LLMAnalyzer(api_key=api_key, base_url=base_url)
    return analyzer.suggest_breakpoints(start_func, end_func)
