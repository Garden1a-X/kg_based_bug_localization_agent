#!/usr/bin/env python3
"""
LLM辅助的Bug定位流程
结合大语言模型和知识图谱进行bug定位
"""

import json
from typing import List, Dict, Tuple
from agents.llm_analyzer import LLMAnalyzer
from data.kg_interface import KnowledgeGraphInterface


class LLMAssistedLocalization:
    """LLM辅助的Bug定位系统"""

    def __init__(
        self,
        kg_interface: KnowledgeGraphInterface,
        llm_api_key: str = "",
        llm_base_url: str = "http://10.88.3.81:8502"
    ):
        """
        初始化

        Args:
            kg_interface: 知识图谱接口
            llm_api_key: LLM API密钥
            llm_base_url: LLM API服务地址
        """
        self.kg = kg_interface
        self.llm = LLMAnalyzer(api_key=llm_api_key, base_url=llm_base_url)

    def localize_from_log(self, bug_log: str, context: str = None) -> Dict:
        """
        从bug日志定位问题函数

        Args:
            bug_log: bug日志内容
            context: 可选的上下文信息

        Returns:
            {
                "llm_analysis": {...},  # LLM分析结果
                "matched_functions": {...},  # 在KG中匹配到的函数
                "call_chains": [...]  # 可能的调用链
            }
        """
        print("="*80)
        print("步骤1: 使用LLM分析bug日志")
        print("="*80)

        # 使用LLM分析日志
        llm_result = self.llm.analyze_bug_log(bug_log, context)

        print(f"\nLLM分析结果:")
        print(f"  起始函数: {llm_result.get('entry_functions', [])}")
        print(f"  中间函数: {llm_result.get('intermediate_functions', [])}")
        print(f"  错误函数: {llm_result.get('error_functions', [])}")
        if llm_result.get('reasoning'):
            print(f"\n  推理: {llm_result['reasoning']}")

        print("\n" + "="*80)
        print("步骤2: 在知识图谱中搜索函数")
        print("="*80)

        # 在知识图谱中搜索这些函数
        matched_functions = self._search_functions_in_kg(llm_result)

        print(f"\n匹配结果:")
        for category, funcs in matched_functions.items():
            if funcs:
                print(f"\n  {category}:")
                for func_name, func_ids in funcs.items():
                    print(f"    {func_name}: 找到 {len(func_ids)} 个实例")
                    for func_id in func_ids[:3]:  # 最多显示3个
                        func_info = self.kg.get_function_info(func_id)
                        if func_info:
                            print(f"      - ID={func_id}, 文件: {func_info.get('source_file', 'N/A')}")

        print("\n" + "="*80)
        print("步骤3: 构建可能的调用链")
        print("="*80)

        # 构建调用链
        call_chains = self._build_call_chains(matched_functions)

        if call_chains:
            print(f"\n找到 {len(call_chains)} 条可能的调用链:")
            for i, chain in enumerate(call_chains[:5], 1):  # 显示前5条
                print(f"\n  调用链 {i}:")
                print(f"    {' -> '.join(chain['function_names'])}")
                print(f"    长度: {chain['length']} 跳")
        else:
            print("\n未找到完整的调用链，可能需要：")
            print("  - 使用LLM建议中间断点")
            print("  - 或者扩大搜索范围")

        return {
            "llm_analysis": llm_result,
            "matched_functions": matched_functions,
            "call_chains": call_chains
        }

    def _search_functions_in_kg(self, llm_result: Dict) -> Dict[str, Dict[str, List[str]]]:
        """在知识图谱中搜索LLM提取的函数名"""
        matched = {
            "entry_functions": {},
            "intermediate_functions": {},
            "error_functions": {}
        }

        # 搜索每个类别的函数
        for category in ["entry_functions", "intermediate_functions", "error_functions"]:
            func_names = llm_result.get(category, [])
            for func_name in func_names:
                # 在KG中搜索
                func_ids = self.kg.get_function_ids(func_name)
                if func_ids:
                    matched[category][func_name] = func_ids

        return matched

    def _build_call_chains(self, matched_functions: Dict) -> List[Dict]:
        """尝试构建调用链"""
        call_chains = []

        entry_funcs = matched_functions.get("entry_functions", {})
        error_funcs = matched_functions.get("error_functions", {})

        if not entry_funcs or not error_funcs:
            return call_chains

        # 尝试从每个起始函数到每个错误函数的路径
        for entry_name, entry_ids in entry_funcs.items():
            for error_name, error_ids in error_funcs.items():
                for entry_id in entry_ids[:2]:  # 每个名字最多尝试2个实例
                    for error_id in error_ids[:2]:
                        # 简单的BFS搜索（这里可以调用ChainTracerAgent）
                        path = self._find_path_bfs(entry_id, error_id, max_depth=10)
                        if path:
                            call_chains.append({
                                "entry_function": entry_name,
                                "error_function": error_name,
                                "function_ids": path,
                                "function_names": [self.kg.get_function_name(fid) for fid in path],
                                "length": len(path) - 1
                            })

        # 按路径长度排序（短路径优先）
        call_chains.sort(key=lambda x: x['length'])

        return call_chains

    def _find_path_bfs(self, start_id: str, end_id: str, max_depth: int = 10) -> List[str]:
        """使用BFS查找路径（简化版）"""
        from collections import deque

        if start_id == end_id:
            return [start_id]

        queue = deque([(start_id, [start_id])])
        visited = {start_id}

        while queue:
            current_id, path = queue.popleft()

            if len(path) > max_depth:
                continue

            # 获取当前函数调用的函数
            callees = self.kg.get_callees(current_id)

            for callee_id in callees:
                if callee_id == end_id:
                    return path + [callee_id]

                if callee_id not in visited:
                    visited.add(callee_id)
                    queue.append((callee_id, path + [callee_id]))

        return []

    def suggest_breakpoints_with_llm(
        self,
        start_function: str,
        end_function: str,
        knowledge: str = None
    ) -> List[str]:
        """
        使用LLM建议断点函数

        Args:
            start_function: 起始函数名
            end_function: 结束函数名
            knowledge: 领域知识

        Returns:
            建议的中间函数名列表
        """
        print("="*80)
        print("使用LLM建议断点")
        print("="*80)
        print(f"起始函数: {start_function}")
        print(f"结束函数: {end_function}")

        breakpoints = self.llm.suggest_breakpoints(
            start_function, end_function, knowledge
        )

        print(f"\nLLM建议的断点函数:")
        for i, bp in enumerate(breakpoints, 1):
            print(f"  {i}. {bp}")

        # 在KG中验证这些函数是否存在
        print(f"\n在知识图谱中验证:")
        validated = {}
        for bp in breakpoints:
            func_ids = self.kg.get_function_ids(bp)
            if func_ids:
                validated[bp] = func_ids
                print(f"  ✅ {bp}: 找到 {len(func_ids)} 个实例")
            else:
                print(f"  ❌ {bp}: 未找到")

        return list(validated.keys())


def main():
    """示例：使用LLM辅助定位"""

    # 示例bug日志（这是之前的dw_mci例子）
    bug_log = """
[    2.123456] dw_mci_probe: Synopsys Designware Multimedia Card Interface Driver
[    2.234567] dw_mci_probe: allocated host
[    2.345678] dw_mci_init_slot: initializing slot 0
[    2.456789] mmc0: new high speed SDHC card at address 0001
[    2.567890] mmcblk0: mmc0:0001 SD32G 29.7 GiB
[    3.678901] mmcblk0: p1
[   10.123456] mmc0: Timeout waiting for hardware interrupt.
[   10.234567] mmc0: Controller tuning failed
[   10.345678] mmc_execute_tuning: tuning execution failed
[   10.456789] dw_mci_execute_tuning: tuning failed with error -110
    """

    # 初始化知识图谱接口（使用Mock数据）
    print("初始化知识图谱...")
    kg = KnowledgeGraphInterface(data_dir="data")

    # 初始化LLM辅助定位系统
    print("初始化LLM辅助定位系统...")
    localizer = LLMAssistedLocalization(
        kg_interface=kg,
        llm_api_key="",  # 如果需要可以在这里填入
        llm_base_url="http://10.88.3.81:8502"
    )

    print("\n" + "="*80)
    print("开始LLM辅助Bug定位")
    print("="*80)

    # 执行定位
    result = localizer.localize_from_log(
        bug_log=bug_log,
        context="Linux kernel MMC/SD card driver subsystem"
    )

    # 保存结果
    output_file = "llm_localization_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        # 将结果序列化（去除不可序列化的部分）
        json_result = {
            "llm_analysis": result["llm_analysis"],
            "matched_functions": {
                k: {fname: fids for fname, fids in v.items()}
                for k, v in result["matched_functions"].items()
            },
            "call_chains": result["call_chains"]
        }
        json.dump(json_result, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")

    # 示例：使用LLM建议断点
    print("\n" + "="*80)
    print("示例：LLM建议断点")
    print("="*80)

    breakpoints = localizer.suggest_breakpoints_with_llm(
        start_function="dw_mci_probe",
        end_function="dw_mci_execute_tuning",
        knowledge="MMC controller driver initialization and tuning flow"
    )

    print(f"\n验证通过的断点: {breakpoints}")


if __name__ == "__main__":
    main()
