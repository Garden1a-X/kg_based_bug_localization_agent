"""
测试完整的异步调用链检测流程

场景：
  6. _mmc_detect_change (调用者)
  7. mmc_schedule_delayed_work (异步调度函数)
  8. mmc_rescan (异步目标函数)

检测流程：
  1. 发现 6 call 7 (直接调用)
  2. 检查 7 的函数名是否包含异步关键字 → 是
  3. LLM分析 7 的源码，确认是异步调用函数 → 是
  4. LLM分析 6 的源码，找到调用 7 时的参数 → &host->detect
  5. 提取字段名 → detect
  6. 查询图谱 ASSIGNED_TO(?, detect) → 找到 mmc_rescan
  7. 建立 7 --async--> 8 的关系
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.kg_interface import KnowledgeGraphInterface
from openai import OpenAI
import json


# Mock数据：mmc_rescan 赋值给 detect 字段
# TODO: 等图谱完善后删除
MOCK_ASYNC_ASSIGNED_TO = {
    'detect': ['mmc_rescan']  # detect字段 -> 赋值的函数
}


def get_function_source(kg: KnowledgeGraphInterface, func_name: str) -> str:
    """获取函数源代码"""
    func_entity = kg.find_function(func_name)
    if not func_entity:
        return None

    func_id = func_entity.get('id')
    impl_id = kg.normalize_id(func_id)
    impl_entity = kg.entity_by_id.get(impl_id)

    if not impl_entity:
        return None

    source_file = impl_entity.get('source_file')
    start_line = impl_entity.get('start_line')
    end_line = impl_entity.get('end_line')

    if not all([source_file, start_line, end_line]):
        return None

    try:
        with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            code_lines = lines[start_line - 1:end_line]
            return ''.join(code_lines)
    except Exception as e:
        print(f"  ✗ 读取源文件失败: {e}")
        return None


def llm_check_is_async_function(func_name: str, source_code: str) -> bool:
    """
    LLM检查函数是否是异步调用函数

    Args:
        func_name: 函数名
        source_code: 函数源代码

    Returns:
        是否是异步调用函数
    """
    client = OpenAI(api_key="", base_url="http://10.12.208.86:8502")

    prompt = f"""分析以下C函数，判断它是否是异步调用函数（work queue相关）。

函数名: {func_name}
源代码:
```c
{source_code}
```

异步调用函数的特征：
1. 调用了 queue_work() / queue_delayed_work() / schedule_work() 等
2. 参数包含 work_struct 或 delayed_work
3. 用于将任务加入工作队列

请返回JSON格式：
{{
  "is_async_function": true/false,
  "reason": "判断理由"
}}

只返回JSON，不要其他说明。"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a C code analyzer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            timeout=180
        )

        content = response.choices[0].message.content.strip()

        # 解析JSON
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        result = json.loads(content)
        return result.get('is_async_function', False)

    except Exception as e:
        print(f"  ✗ LLM检查失败: {e}")
        return False


def llm_extract_call_parameter(caller_name: str, callee_name: str, caller_source: str) -> str:
    """
    LLM分析调用者源码，提取调用被调用者时传入的work字段名

    Args:
        caller_name: 调用者函数名
        callee_name: 被调用者函数名
        caller_source: 调用者源代码

    Returns:
        字段名（如 'detect'），如果未找到则返回 None
    """
    client = OpenAI(api_key="", base_url="http://10.12.208.86:8502")

    prompt = f"""分析以下C函数，找到它调用 {callee_name} 时传入的work参数。

函数名: {caller_name}
源代码:
```c
{caller_source}
```

任务：
找到调用 {callee_name}(...) 的代码行，提取第一个参数（通常是&var形式）。
如果参数是 &host->detect，则字段名是 detect。
如果参数是 &work，则字段名是 work。

返回JSON格式：
{{
  "found": true/false,
  "call_expression": "完整的调用表达式",
  "first_parameter": "第一个参数的完整形式（如 &host->detect）",
  "field_name": "提取的字段名（如 detect）"
}}

如果没找到调用，返回：
{{
  "found": false
}}

只返回JSON，不要其他说明。"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a C code analyzer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=800,
            timeout=180
        )

        content = response.choices[0].message.content.strip()

        # 解析JSON
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        result = json.loads(content)

        if not result.get('found', False):
            return None

        field_name = result.get('field_name')
        return field_name

    except Exception as e:
        print(f"  ✗ LLM提取参数失败: {e}")
        return None


def query_assigned_to(kg: KnowledgeGraphInterface, field_name: str) -> list:
    """
    查询哪些函数被赋值给指定字段

    Args:
        kg: 知识图谱接口
        field_name: 字段名

    Returns:
        函数名列表
    """
    # 先尝试mock数据
    if field_name in MOCK_ASYNC_ASSIGNED_TO:
        funcs = MOCK_ASYNC_ASSIGNED_TO[field_name]
        print(f"  ℹ 使用Mock数据: {field_name} -> {funcs}")
        return funcs

    # TODO: 查询真实图谱的ASSIGNED_TO关系
    # 1. 找到所有名为field_name的FIELD实体
    # 2. 查询 ASSIGNED_TO(head=field_id, tail=?)
    # 3. 返回tail对应的函数名

    print(f"  ⚠ 图谱中未找到字段 {field_name} 的ASSIGNED_TO关系")
    return []


def test_async_call_chain():
    """测试完整的异步调用链检测"""

    print("=" * 80)
    print("测试异步调用链检测（三函数场景）")
    print("=" * 80)

    # 初始化图谱
    data_dir = "/data/xuao/code_kg_search/linux_test/data/mmc"
    if not Path(data_dir).exists():
        data_dir = "/data/xuao/code_kg_search/linux_test/data"

    kg = KnowledgeGraphInterface(data_dir)

    # 三个函数
    func_6 = "_mmc_detect_change"     # 调用者
    func_7 = "mmc_schedule_delayed_work"  # 异步调度函数
    func_8_expected = "mmc_rescan"    # 期望的异步目标

    print(f"\n场景：")
    print(f"  6. {func_6} (调用者)")
    print(f"  7. {func_7} (异步调度函数)")
    print(f"  8. {func_8_expected} (期望的异步目标)")

    # === 步骤1: 确认6 call 7 ===
    print(f"\n{'='*80}")
    print(f"[步骤1] 确认直接调用关系: {func_6} → {func_7}")
    print(f"{'='*80}")

    # 这里简化，假设已知6 call 7（实际可以从图谱查询）
    print(f"  ✓ 已知: {func_6} 直接调用 {func_7}")

    # === 步骤2: 检查7是否符合异步关键字 ===
    print(f"\n{'='*80}")
    print(f"[步骤2] 检查函数名关键字: {func_7}")
    print(f"{'='*80}")

    has_async_keyword = 'schedule' in func_7.lower() or 'delayed_work' in func_7.lower()
    print(f"  函数名: {func_7}")
    print(f"  包含异步关键字: {has_async_keyword}")

    if not has_async_keyword:
        print(f"  ✗ 不是异步函数，结束")
        kg.close()
        return

    # === 步骤3: LLM确认7是异步调用函数 ===
    print(f"\n{'='*80}")
    print(f"[步骤3] LLM确认是否为异步调用函数")
    print(f"{'='*80}")

    source_7 = get_function_source(kg, func_7)
    if not source_7:
        print(f"  ✗ 无法获取 {func_7} 的源代码")
        kg.close()
        return

    print(f"  → 调用LLM分析 {func_7}...")
    is_async = llm_check_is_async_function(func_7, source_7)
    print(f"  ← LLM判断: {is_async}")

    if not is_async:
        print(f"  ✗ LLM判断不是异步函数，结束")
        kg.close()
        return

    # === 步骤4: LLM分析6的源码，提取调用参数 ===
    print(f"\n{'='*80}")
    print(f"[步骤4] LLM分析调用参数: {func_6} 调用 {func_7} 时的参数")
    print(f"{'='*80}")

    source_6 = get_function_source(kg, func_6)
    if not source_6:
        print(f"  ✗ 无法获取 {func_6} 的源代码")
        kg.close()
        return

    print(f"  源代码预览（{func_6}）:")
    print("  " + "-" * 76)
    code_lines = source_6.split('\n')
    for line in code_lines[:20]:
        print(f"  {line}")
    if len(code_lines) > 20:
        print(f"  ... (共 {len(code_lines)} 行)")
    print("  " + "-" * 76)

    print(f"\n  → 调用LLM提取参数...")
    field_name = llm_extract_call_parameter(func_6, func_7, source_6)

    if not field_name:
        print(f"  ✗ 无法提取字段名")
        kg.close()
        return

    print(f"  ← LLM提取到字段名: {field_name}")

    # === 步骤5: 查询ASSIGNED_TO关系 ===
    print(f"\n{'='*80}")
    print(f"[步骤5] 查询 ASSIGNED_TO(?, {field_name})")
    print(f"{'='*80}")

    async_targets = query_assigned_to(kg, field_name)

    if not async_targets:
        print(f"  ✗ 未找到赋值给 {field_name} 的函数")
        kg.close()
        return

    print(f"  ✓ 找到 {len(async_targets)} 个目标函数:")
    for target in async_targets:
        print(f"    - {target}")

    # === 步骤6: 建立异步调用关系 ===
    print(f"\n{'='*80}")
    print(f"[步骤6] 建立异步调用关系")
    print(f"{'='*80}")

    for target in async_targets:
        print(f"\n  建立关系: {func_7} --[async]--> {target}")
        print(f"    桥接类型: async")
        print(f"    work字段: {field_name}")
        print(f"    检测方法: llm_analysis + graph_query")

    # === 最终结果 ===
    print(f"\n{'='*80}")
    print(f"最终调用链")
    print(f"{'='*80}")

    print(f"\n  {func_6}")
    print(f"    ↓ (直接调用)")
    print(f"  {func_7}")
    print(f"    ↓ (异步调用, 字段={field_name})")
    for target in async_targets:
        print(f"  {target}")

    # 验证
    if func_8_expected in async_targets:
        print(f"\n  ✅ 成功！找到了期望的目标函数 {func_8_expected}")
    else:
        print(f"\n  ⚠️ 警告：未找到期望的目标函数 {func_8_expected}")

    kg.close()


if __name__ == "__main__":
    test_async_call_chain()
