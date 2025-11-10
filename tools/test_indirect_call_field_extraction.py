#!/usr/bin/env python3
"""
测试间接调用字段提取功能

方案：
1. 配置哪些函数需要检测间接调用
2. 用LLM分析函数源码，提取间接调用的字段名
3. 在图谱的ASSIGNED_TO关系中查询该字段名，找到所有可能的目标函数
4. 返回候选函数列表，供BFS探索

独立测试脚本，不合并进主流程
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
import json
from openai import OpenAI

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.kg_interface import KnowledgeGraphInterface


class IndirectCallFieldExtractor:
    """间接调用字段提取器"""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "http://10.12.208.86:8502",
        model: str = "gpt-4o-mini"
    ):
        """
        初始化

        Args:
            api_key: OpenAI API密钥
            base_url: API服务地址
            model: 使用的模型
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.timeout = 180

    def extract_indirect_call_fields(self, func_name: str, source_code: str) -> List[Dict]:
        """
        从函数源码中提取间接调用的字段名

        Args:
            func_name: 函数名（用于日志）
            source_code: 函数源代码

        Returns:
            [
                {
                    "expression": "host->ops->execute_tuning(host, opcode)",
                    "field_name": "execute_tuning",
                    "call_line_in_function": 12  # 可选
                },
                ...
            ]
        """
        prompt = self._build_extraction_prompt(source_code)

        try:
            print(f"  → 调用LLM分析 {func_name} 的源码...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in C code analysis, specializing in identifying function pointer calls."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                timeout=self.timeout
            )

            content = response.choices[0].message.content.strip()
            print(f"  ✓ LLM响应完成")

            # 解析JSON
            result = self._parse_llm_response(content)
            return result

        except Exception as e:
            print(f"  ✗ LLM分析失败: {e}")
            return []

    def _build_extraction_prompt(self, source_code: str) -> str:
        """构建提取prompt"""
        prompt = f"""分析以下C函数，识别所有通过函数指针的间接调用。

函数代码：
```c
{source_code}
```

任务：
1. 找出所有形如 `ptr->field(...)` 或 `(*ptr->field)(...)` 的间接调用
2. 提取字段名（field的名字，即最后一级的字段）
3. 如果有多层嵌套（如 `host->ops->execute_tuning`），提取最后一级字段名（`execute_tuning`）

返回JSON格式：
```json
{{
  "indirect_calls": [
    {{
      "expression": "完整的调用表达式",
      "field_name": "字段名（最后一级）",
      "explanation": "简短说明（可选）"
    }}
  ]
}}
```

注意事项：
- 只关注实际的函数调用，忽略NULL检查等判断语句
- 如果有多个间接调用，全部列出
- 字段名应该是可以在图谱中查询的标识符
- 如果没有找到间接调用，返回空数组

示例：
```c
// 对于这样的代码：
if (host->ops && host->ops->execute_tuning)
    err = host->ops->execute_tuning(host, opcode);

// 应该返回：
{{
  "indirect_calls": [
    {{
      "expression": "host->ops->execute_tuning(host, opcode)",
      "field_name": "execute_tuning",
      "explanation": "Function pointer call through ops table"
    }}
  ]
}}
```
"""
        return prompt

    def _parse_llm_response(self, content: str) -> List[Dict]:
        """解析LLM响应"""
        try:
            # 提取JSON代码块
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

            # 提取indirect_calls列表
            indirect_calls = data.get("indirect_calls", [])

            if not indirect_calls:
                print(f"  ℹ️  LLM未发现间接调用")
                return []

            print(f"  ✓ LLM发现 {len(indirect_calls)} 个间接调用:")
            for call in indirect_calls:
                print(f"    - 字段: {call.get('field_name')}")
                print(f"      表达式: {call.get('expression', 'N/A')}")

            return indirect_calls

        except json.JSONDecodeError as e:
            print(f"  ✗ JSON解析失败: {e}")
            print(f"  LLM原始输出:\n{content}")
            return []
        except Exception as e:
            print(f"  ✗ 解析失败: {e}")
            return []


class AssignedToQueryHelper:
    """ASSIGNED_TO关系查询助手"""

    def __init__(self, kg: KnowledgeGraphInterface):
        """
        初始化

        Args:
            kg: 知识图谱接口
        """
        self.kg = kg

    def query_by_field_name(self, field_name: str) -> List[Dict]:
        """
        根据字段名查询ASSIGNED_TO关系

        Args:
            field_name: 字段名（如 "execute_tuning"）

        Returns:
            [
                {
                    "target_function": "dw_mci_execute_tuning",
                    "field_name": "execute_tuning",
                    "context_var_id": "6344"
                },
                ...
            ]
        """
        if 'ASSIGNED_TO' not in self.kg.relations:
            print(f"  ⚠️  图谱中没有ASSIGNED_TO关系")
            return []

        results = []
        for rel in self.kg.relations['ASSIGNED_TO']:
            # ASSIGNED_TO关系的结构需要根据实际图谱确定
            # 可能的字段：head（字段实体ID）, tail（函数实体ID）, field_name等
            rel_field_name = rel.get('field_name') or rel.get('name')

            if rel_field_name == field_name:
                # 找到匹配的字段
                tail_id = rel.get('tail')  # 目标函数ID

                # 查询函数名
                target_entity = self.kg.entity_by_id.get(tail_id)
                if target_entity:
                    target_func_name = target_entity.get('name')
                    results.append({
                        'target_function': target_func_name,
                        'field_name': field_name,
                        'context_var_id': rel.get('context_var_id', 'N/A'),
                        'head_id': rel.get('head'),
                        'tail_id': tail_id
                    })

        return results


def test_single_function(
    kg: KnowledgeGraphInterface,
    extractor: IndirectCallFieldExtractor,
    query_helper: AssignedToQueryHelper,
    func_name: str
):
    """
    测试单个函数的间接调用检测

    Args:
        kg: 知识图谱接口
        extractor: 字段提取器
        query_helper: 查询助手
        func_name: 函数名
    """
    print(f"\n{'='*80}")
    print(f"测试函数: {func_name}")
    print(f"{'='*80}")

    # 1. 在图谱中查找函数（处理同名函数）
    print(f"\n[1/4] 在图谱中查找函数...")

    # 获取该函数名的所有ID
    all_func_ids = kg.func_name_to_ids.get(func_name, [])

    if not all_func_ids:
        print(f"  ✗ 函数 {func_name} 不存在")
        return

    print(f"  ✓ 找到函数: {func_name} ({len(all_func_ids)} 个实例)")

    # 找到有源码的实体（优先选择实现，即 is_declaration=False）
    func_entity = None
    for func_id in all_func_ids:
        entity = kg.entity_by_id.get(func_id)
        if not entity:
            continue

        is_decl = entity.get('is_declaration', False)
        source_file = entity.get('source_file', '')

        print(f"    - ID {func_id}: {source_file} (is_declaration={is_decl})")

        # 优先选择实现（非声明）
        if not is_decl:
            func_entity = entity
            print(f"      → 选择此实现")
            break

    # 如果没有实现，使用第一个
    if not func_entity and all_func_ids:
        func_entity = kg.entity_by_id.get(all_func_ids[0])
        print(f"      → 未找到实现，使用第一个")

    if not func_entity:
        print(f"  ✗ 无法获取函数实体")
        return

    print(f"  ✓ 最终选择:")
    print(f"    ID: {func_entity.get('id')}")
    print(f"    文件: {func_entity.get('source_file', 'N/A')}")
    print(f"    is_declaration: {func_entity.get('is_declaration', 'N/A')}")

    # 2. 获取函数源码
    print(f"\n[2/4] 获取函数源码...")

    # 尝试从实体中获取源码
    source_code = func_entity.get('code') or func_entity.get('body')

    # 如果实体中没有存储源码，从源文件读取
    if not source_code:
        source_file = func_entity.get('source_file')
        start_line = func_entity.get('start_line')
        end_line = func_entity.get('end_line')

        if source_file and start_line and end_line:
            print(f"  实体中无源码，尝试从文件读取...")
            print(f"    文件: {source_file}")
            print(f"    行范围: {start_line}-{end_line}")

            try:
                with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # 注意：行号从1开始，但列表索引从0开始
                    source_code = ''.join(lines[start_line-1:end_line])
                print(f"  ✓ 从文件读取成功")
            except FileNotFoundError:
                print(f"  ✗ 源文件不存在: {source_file}")
                return
            except Exception as e:
                print(f"  ✗ 读取源文件失败: {e}")
                return
        else:
            print(f"  ✗ 实体缺少源文件信息")
            print(f"    source_file: {source_file}")
            print(f"    start_line: {start_line}")
            print(f"    end_line: {end_line}")
            return

    if not source_code:
        print(f"  ✗ 无法获取源码")
        return

    print(f"  ✓ 获取源码成功")
    print(f"    代码长度: {len(source_code)} 字符")
    print(f"    代码行数: {len(source_code.splitlines())} 行")
    print(f"    前150字符: {source_code[:150]}...")

    # 3. LLM提取间接调用字段
    print(f"\n[3/4] LLM提取间接调用字段...")

    indirect_calls = extractor.extract_indirect_call_fields(func_name, source_code)

    if not indirect_calls:
        print(f"  ℹ️  未发现间接调用（可能该函数没有间接调用）")
        return

    # 4. 查询ASSIGNED_TO关系
    print(f"\n[4/4] 查询图谱ASSIGNED_TO关系...")

    all_candidates = []

    for call_info in indirect_calls:
        field_name = call_info.get('field_name')
        print(f"\n  查询字段: {field_name}")

        candidates = query_helper.query_by_field_name(field_name)

        if candidates:
            print(f"    ✓ 找到 {len(candidates)} 个候选函数:")
            for i, cand in enumerate(candidates, 1):
                print(f"      {i}. {cand['target_function']}")
                print(f"         context_var_id: {cand.get('context_var_id', 'N/A')}")
            all_candidates.extend(candidates)
        else:
            print(f"    ✗ 未找到ASSIGNED_TO关系（字段: {field_name}）")

    # 5. 总结
    print(f"\n{'='*80}")
    print(f"总结")
    print(f"{'='*80}")
    print(f"函数: {func_name}")
    print(f"发现间接调用: {len(indirect_calls)} 个")
    print(f"候选目标函数: {len(all_candidates)} 个")

    if all_candidates:
        print(f"\n可用于BFS探索的候选函数:")
        unique_funcs = list(set([c['target_function'] for c in all_candidates]))
        for func in unique_funcs:
            print(f"  - {func}")

    return {
        'func_name': func_name,
        'indirect_calls': indirect_calls,
        'candidates': all_candidates
    }


def main():
    """主函数"""
    print("="*80)
    print("间接调用字段提取 - 独立测试")
    print("="*80)

    # 初始化组件
    print("\n[初始化] 加载知识图谱...")
    kg = KnowledgeGraphInterface(
        data_dir="/data/xuao/code_kg_search/linux_test/data/mmc"
    )
    print("  ✓ 知识图谱加载完成")

    print("\n[初始化] 创建LLM提取器...")
    extractor = IndirectCallFieldExtractor()
    print("  ✓ LLM提取器初始化完成")

    print("\n[初始化] 创建查询助手...")
    query_helper = AssignedToQueryHelper(kg)
    print("  ✓ 查询助手初始化完成")

    # 测试函数列表（这些是需要检测间接调用的函数）
    test_functions = [
        "mmc_execute_tuning",     # 应该能找到 execute_tuning 字段
        # "dw_mci_init_slot",      # 如果需要，可以测试更多函数
    ]

    results = []

    for func_name in test_functions:
        try:
            result = test_single_function(kg, extractor, query_helper, func_name)
            if result:
                results.append(result)
        except Exception as e:
            print(f"\n✗ 测试 {func_name} 失败: {e}")
            import traceback
            traceback.print_exc()

    # 最终报告
    print("\n" + "="*80)
    print("最终报告")
    print("="*80)

    for result in results:
        print(f"\n函数: {result['func_name']}")
        print(f"  间接调用: {len(result['indirect_calls'])} 个")
        print(f"  候选函数: {len(result['candidates'])} 个")

        if result['candidates']:
            candidate_names = list(set([c['target_function'] for c in result['candidates']]))
            print(f"  候选列表: {', '.join(candidate_names)}")

    print("\n" + "="*80)
    print("测试完成")
    print("="*80)

    if any(r['candidates'] for r in results):
        print("\n✅ 方案可行！LLM成功提取字段名并在图谱中找到候选函数。")
        print("   下一步可以将此功能集成到 _find_indirect_callees() 中。")
    else:
        print("\n⚠️  未找到候选函数，可能需要调整：")
        print("   1. 检查ASSIGNED_TO关系的数据结构")
        print("   2. 检查字段名匹配逻辑")
        print("   3. 检查LLM提取的字段名是否准确")

    kg.close()


if __name__ == "__main__":
    main()
