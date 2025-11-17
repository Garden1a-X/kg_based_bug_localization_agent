#!/usr/bin/env python3
"""
测试日志匹配逻辑
演示如何从日志逐行匹配到FAIL_MESSAGE实体，推断关键函数
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.mock_indirect_calls import (
    MOCK_FAIL_MESSAGES,
    _extract_message_pattern
)
import re


def match_log_line_to_fail_message(log_line: str, fail_messages: dict) -> list:
    """
    尝试将一行日志匹配到FAIL_MESSAGE实体

    Args:
        log_line: 单行日志文本
        fail_messages: FAIL_MESSAGE实体字典

    Returns:
        匹配到的消息列表 [(msg_id, msg_data, matched_text, similarity), ...]
    """
    matches = []

    for msg_id, msg_data in fail_messages.items():
        # 从name字段提取匹配模式
        pattern = _extract_message_pattern(msg_data.get('name', ''))
        if not pattern:
            continue

        # 尝试匹配
        match_obj = re.search(pattern, log_line, re.IGNORECASE)
        if match_obj:
            matched_text = match_obj.group(0)

            # 计算相似度（匹配长度占日志行的比例）
            similarity = len(matched_text) / len(log_line.strip()) if log_line.strip() else 0

            matches.append((msg_id, msg_data, matched_text, similarity))

    # 按相似度排序（从高到低）
    matches.sort(key=lambda x: x[3], reverse=True)

    return matches


def analyze_log_by_lines(log_text: str) -> dict:
    """
    逐行分析日志，匹配FAIL_MESSAGE

    Args:
        log_text: 完整日志文本

    Returns:
        分析结果
    """
    lines = [line.strip() for line in log_text.strip().split('\n') if line.strip()]

    result = {
        'total_lines': len(lines),
        'line_matches': [],
        'all_functions': []
    }

    print("=" * 70)
    print("逐行分析日志")
    print("=" * 70)

    for idx, line in enumerate(lines, 1):
        print(f"\n【第{idx}行】 {line}")

        matches = match_log_line_to_fail_message(line, MOCK_FAIL_MESSAGES)

        if matches:
            # 取最佳匹配（相似度最高）
            best_msg_id, best_msg, matched_text, similarity = matches[0]
            func_name = best_msg.get('scope')

            print(f"  ✓ 匹配成功!")
            print(f"    匹配文本: '{matched_text}'")
            print(f"    相似度: {similarity:.2%}")
            print(f"    推断函数: {func_name}")
            print(f"    源文件: {best_msg.get('source_file')}:{best_msg.get('start_line')}")

            # 显示FAIL_MESSAGE的原始name
            print(f"    原始代码: {best_msg.get('name')}")

            result['line_matches'].append({
                'line_number': idx,
                'log_line': line,
                'matched_text': matched_text,
                'similarity': similarity,
                'function': func_name,
                'message_id': best_msg_id,
                'source_file': best_msg.get('source_file'),
                'start_line': best_msg.get('start_line')
            })

            if func_name and func_name not in result['all_functions']:
                result['all_functions'].append(func_name)

            # 如果有多个匹配，显示其他候选
            if len(matches) > 1:
                print(f"    其他候选:")
                for msg_id, msg, txt, sim in matches[1:]:
                    print(f"      - {msg.get('scope')} (相似度: {sim:.2%})")
        else:
            print(f"  ✗ 未匹配到FAIL_MESSAGE")

    return result


def display_summary(result: dict):
    """显示分析汇总"""
    print("\n" + "=" * 70)
    print("分析汇总")
    print("=" * 70)

    print(f"\n总日志行数: {result['total_lines']}")
    print(f"成功匹配: {len(result['line_matches'])} 行")
    print(f"推断出的函数: {len(result['all_functions'])} 个")

    if result['all_functions']:
        print("\n关键函数列表（按日志出现顺序）:")
        for idx, func in enumerate(result['all_functions'], 1):
            print(f"  {idx}. {func}")

        print("\n💡 调用链顺序（逆序，因为日志是栈式）:")
        print(f"  入口 → {' → '.join(reversed(result['all_functions']))} → 错误点")


def main():
    """主测试函数"""
    # 测试日志
    mmc_error_log = """
ALL phases bad!
mmc0: tuning execution failed: -1
mmc0: error -1 whilst initialising MMC card
    """

    print("\n测试日志:")
    print("-" * 70)
    print(mmc_error_log.strip())
    print("-" * 70)

    # 逐行分析
    result = analyze_log_by_lines(mmc_error_log)

    # 显示汇总
    display_summary(result)

    print("\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)

    return result


if __name__ == "__main__":
    main()
