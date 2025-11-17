"""
测试异步调用检测功能

目标：
1. 识别可能包含异步调用的函数（基于函数名关键字）
2. 使用LLM分析源码，检测是否真的有异步调用
3. 提取异步调用的目标函数

示例：
  mmc_schedule_delayed_work 包含关键字 'schedule' 和 'delayed_work'
  源码中有 INIT_DELAYED_WORK(&host->detect, mmc_rescan)
  → 检测到异步调用目标: mmc_rescan
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.kg_interface import KnowledgeGraphInterface
from openai import OpenAI
import json


# 异步调用关键字规则
ASYNC_KEYWORDS = [
    'schedule',
    'delayed_work',
    'queue_work',
    'schedule_work',
    'init_work',
    'async',
]


def is_async_function(func_name: str) -> bool:
    """
    判断函数名是否包含异步调用关键字

    Args:
        func_name: 函数名

    Returns:
        是否可能是异步调用函数
    """
    func_name_lower = func_name.lower()
    for keyword in ASYNC_KEYWORDS:
        if keyword in func_name_lower:
            return True
    return False


def get_function_source_code(kg: KnowledgeGraphInterface, func_name: str) -> str:
    """
    获取函数的源代码

    Args:
        kg: 知识图谱接口
        func_name: 函数名

    Returns:
        函数源代码
    """
    # 1. 查找函数实体
    func_entity = kg.find_function(func_name)
    if not func_entity:
        return None

    # 2. 获取实现ID（declaration需要映射到implementation）
    func_id = func_entity.get('id')
    impl_id = kg.normalize_id(func_id)
    impl_entity = kg.entity_by_id.get(impl_id)

    if not impl_entity:
        print(f"  ⚠ 未找到函数实现: {func_name}")
        return None

    # 3. 读取源文件
    source_file = impl_entity.get('source_file')
    start_line = impl_entity.get('start_line')
    end_line = impl_entity.get('end_line')

    if not all([source_file, start_line, end_line]):
        print(f"  ⚠ 缺少位置信息: {func_name}")
        return None

    # 4. 读取文件内容
    try:
        with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            # 行号从1开始，列表索引从0开始
            code_lines = lines[start_line - 1:end_line]
            return ''.join(code_lines)
    except Exception as e:
        print(f"  ⚠ 读取源文件失败: {e}")
        return None


def detect_async_calls_with_llm(func_name: str, source_code: str) -> list:
    """
    使用LLM检测异步调用

    Args:
        func_name: 函数名
        source_code: 源代码

    Returns:
        [(target_func, bridge_info), ...] 列表
    """
    # 初始化OpenAI客户端
    client = OpenAI(
        api_key="",  # 空字符串也可以
        base_url="http://10.12.208.86:8502"
    )
    model = "gpt-4o-mini"

    prompt = f"""请分析以下C语言函数，检测是否有异步调用（work queue相关）。

函数名: {func_name}

源代码:
```c
{source_code}
```

请查找以下异步调用模式：
1. INIT_DELAYED_WORK(&var, callback_func)
2. INIT_WORK(&var, callback_func)
3. queue_work(wq, &work)
4. schedule_work(&work)
5. schedule_delayed_work(&work, delay)

如果找到异步调用，请返回JSON格式：
{{
  "has_async": true,
  "callbacks": [
    {{
      "callback_function": "目标函数名",
      "work_struct_var": "work结构体变量名",
      "init_macro": "初始化宏名称（如INIT_DELAYED_WORK）",
      "bridge_type": "async"
    }}
  ]
}}

如果没有异步调用，返回：
{{
  "has_async": false,
  "callbacks": []
}}

只返回JSON，不要其他说明。"""

    print(f"\n  → 调用LLM分析异步调用...")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in C code analysis, specializing in identifying async work queue patterns."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
            timeout=180
        )

        response_content = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  ✗ LLM调用失败: {e}")
        return []

    print(f"  ← LLM返回: {response_content[:200]}...")

    # 解析响应
    try:
        # 提取JSON（处理可能的markdown代码块）
        json_text = response_content
        if '```json' in response_content:
            json_text = response_content.split('```json')[1].split('```')[0].strip()
        elif '```' in response_content:
            json_text = response_content.split('```')[1].split('```')[0].strip()

        result = json.loads(json_text)

        if not result.get('has_async', False):
            print(f"  ✓ LLM判断：无异步调用")
            return []

        # 构造返回结果
        async_callees = []
        for callback_info in result.get('callbacks', []):
            target_func = callback_info.get('callback_function')
            if target_func:
                bridge_info = {
                    'bridge_type': 'async',
                    'bridge_entity': callback_info.get('work_struct_var', 'work_struct'),
                    'init_func': callback_info.get('init_macro', 'INIT_WORK'),
                    'method': 'llm_analysis',  # 标记为LLM检测
                    'description': f'异步调用通过 {callback_info.get("init_macro")} 调度 {target_func}'
                }
                async_callees.append((target_func, bridge_info))

        print(f"  ✓ LLM检测到 {len(async_callees)} 个异步调用")
        return async_callees

    except json.JSONDecodeError as e:
        print(f"  ✗ JSON解析失败: {e}")
        print(f"    原始响应: {response_content}")
        return []
    except Exception as e:
        print(f"  ✗ 处理响应失败: {e}")
        return []


def test_specific_function():
    """测试特定函数：mmc_schedule_delayed_work"""

    print("=" * 80)
    print("测试异步调用检测")
    print("=" * 80)

    # 初始化图谱
    data_dir = "/data/xuao/code_kg_search/linux_test/data/mmc"
    if not Path(data_dir).exists():
        data_dir = "/data/xuao/code_kg_search/linux_test/data"

    print(f"\n加载知识图谱: {data_dir}")
    kg = KnowledgeGraphInterface(data_dir)

    # 测试函数
    test_func = "mmc_schedule_delayed_work"

    print(f"\n{'='*80}")
    print(f"测试函数: {test_func}")
    print(f"{'='*80}")

    # 1. 检查关键字匹配
    print(f"\n[步骤1] 检查函数名关键字")
    is_async = is_async_function(test_func)
    print(f"  函数名: {test_func}")
    print(f"  包含异步关键字: {is_async}")

    if not is_async:
        print(f"  ✗ 不匹配异步调用模式，跳过")
        return

    # 2. 获取源代码
    print(f"\n[步骤2] 获取函数源代码")
    source_code = get_function_source_code(kg, test_func)

    if not source_code:
        print(f"  ✗ 无法获取源代码")
        return

    print(f"  ✓ 成功读取源代码 ({len(source_code)} 字符)")
    print(f"\n  源代码预览:")
    print("  " + "-" * 76)
    code_lines = source_code.split('\n')
    for line in code_lines[:15]:
        print(f"  {line}")
    if len(code_lines) > 15:
        print(f"  ... (共 {len(code_lines)} 行)")
    print("  " + "-" * 76)

    # 3. LLM检测
    print(f"\n[步骤3] LLM分析异步调用")
    async_callees = detect_async_calls_with_llm(test_func, source_code)

    # 4. 显示结果
    print(f"\n{'='*80}")
    print(f"检测结果")
    print(f"{'='*80}")

    if async_callees:
        print(f"\n✓ 找到 {len(async_callees)} 个异步调用目标:\n")
        for target_func, bridge_info in async_callees:
            print(f"  • {test_func} --[异步]--> {target_func}")
            print(f"    桥接类型: {bridge_info.get('bridge_type')}")
            print(f"    初始化宏: {bridge_info.get('init_func')}")
            print(f"    work变量: {bridge_info.get('bridge_entity')}")
            print(f"    检测方法: {bridge_info.get('method')}")
            print()
    else:
        print(f"\n✗ 未检测到异步调用")

    kg.close()


def test_multiple_functions():
    """测试多个可能的异步函数"""

    print("=" * 80)
    print("批量测试异步调用检测")
    print("=" * 80)

    # 初始化图谱
    data_dir = "/data/xuao/code_kg_search/linux_test/data/mmc"
    if not Path(data_dir).exists():
        data_dir = "/data/xuao/code_kg_search/linux_test/data"

    kg = KnowledgeGraphInterface(data_dir)

    # 候选函数列表（基于关键字筛选）
    candidate_funcs = [
        "mmc_schedule_delayed_work",
        "queue_delayed_work",
        # 可以添加更多候选函数
    ]

    results = {}

    for func_name in candidate_funcs:
        print(f"\n{'='*80}")
        print(f"测试: {func_name}")
        print(f"{'='*80}")

        # 检查关键字
        if not is_async_function(func_name):
            print(f"  跳过：不匹配异步关键字")
            results[func_name] = None
            continue

        # 获取源码
        source_code = get_function_source_code(kg, func_name)
        if not source_code:
            print(f"  跳过：无法获取源代码")
            results[func_name] = None
            continue

        # LLM检测
        async_callees = detect_async_calls_with_llm(func_name, source_code)
        results[func_name] = async_callees

        if async_callees:
            print(f"  ✓ 找到 {len(async_callees)} 个异步调用")
        else:
            print(f"  ✗ 未检测到异步调用")

    # 汇总结果
    print(f"\n{'='*80}")
    print(f"汇总结果")
    print(f"{'='*80}")

    for func_name, callees in results.items():
        if callees:
            print(f"\n{func_name}:")
            for target, _ in callees:
                print(f"  → {target}")

    kg.close()


if __name__ == "__main__":
    # 测试单个函数
    test_specific_function()

    # 如果需要测试多个函数，取消注释下面这行
    # test_multiple_functions()
