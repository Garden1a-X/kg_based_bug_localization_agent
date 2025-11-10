"""
Mock 间接调用关系数据
TODO: 临时模块，等知识图谱修复 ASSIGNED_TO 关系后删除

这个模块存放已知的间接调用关系，用于在图谱数据不完整时测试框架逻辑。
包括：
1. 异步调用（work_struct）
2. 函数指针（ops 表）
"""

# ============================================================
# TODO: 等图谱修复后删除这个文件
# ============================================================

# 异步调用关系（工作队列）
# 格式：{(caller_func, callee_func): bridge_info}
MOCK_ASYNC_CALLS = {
    # [位置8] mmc_schedule_delayed_work 异步调度 mmc_rescan
    # 这是16节点完整路径中的真实异步调用断点
    ("mmc_schedule_delayed_work", "mmc_rescan"): {
        "bridge_type": "async",
        "bridge_entity": "work_struct.func",
        "init_func": "INIT_DELAYED_WORK",
        "description": "mmc_schedule_delayed_work 通过 work_struct 异步调度 mmc_rescan"
    },
    # 可以添加更多已知的异步调用关系
}

# 函数指针调用关系（ops 表）
# 格式：{(caller_func, callee_func): bridge_info}
MOCK_FUNCTION_POINTER_CALLS = {
    # [位置14] mmc_execute_tuning → dw_mci_execute_tuning（函数指针/ops调用）
    ("mmc_execute_tuning", "dw_mci_execute_tuning"): {
        "bridge_type": "function_pointer",
        "bridge_entity": "mmc_host_ops.execute_tuning",
        "struct_name": "dw_mci_ops",
        "field_name": "execute_tuning",
        "description": "host->ops->execute_tuning() 指向 dw_mci_execute_tuning"
    },

    # [位置15] dw_mci_execute_tuning → dw_mci_hi3660_execute_tuning（函数指针/平台特定ops）
    ("dw_mci_execute_tuning", "dw_mci_hi3660_execute_tuning"): {
        "bridge_type": "function_pointer",
        "bridge_entity": "dw_mci_drv_data.execute_tuning",
        "struct_name": "dw_mci_drv_data",
        "field_name": "execute_tuning",
        "description": "平台特定的 execute_tuning 实现"
    },

    # 可以添加更多已知的函数指针关系
}


def get_mock_async_bridge(caller: str, callee: str) -> dict:
    """
    获取 mock 的异步调用桥接信息

    TODO: 等图谱修复后删除此函数

    Args:
        caller: 调用者函数名
        callee: 被调用者函数名

    Returns:
        桥接信息 dict 或 None
    """
    return MOCK_ASYNC_CALLS.get((caller, callee))


def get_mock_function_pointer_bridge(caller: str, callee: str) -> dict:
    """
    获取 mock 的函数指针桥接信息

    TODO: 等图谱修复后删除此函数

    Args:
        caller: 调用者函数名
        callee: 被调用者函数名

    Returns:
        桥接信息 dict 或 None
    """
    return MOCK_FUNCTION_POINTER_CALLS.get((caller, callee))


def has_mock_indirect_call(caller: str, callee: str) -> bool:
    """
    检查是否存在 mock 的间接调用关系

    TODO: 等图谱修复后删除此函数

    Args:
        caller: 调用者函数名
        callee: 被调用者函数名

    Returns:
        是否存在间接调用关系
    """
    return (
        (caller, callee) in MOCK_ASYNC_CALLS or
        (caller, callee) in MOCK_FUNCTION_POINTER_CALLS
    )


def get_all_mock_relations():
    """
    获取所有 mock 关系（用于调试）

    TODO: 等图谱修复后删除此函数

    Returns:
        所有 mock 关系的列表
    """
    relations = []

    for (caller, callee), info in MOCK_ASYNC_CALLS.items():
        relations.append({
            "type": "async",
            "caller": caller,
            "callee": callee,
            "info": info
        })

    for (caller, callee), info in MOCK_FUNCTION_POINTER_CALLS.items():
        relations.append({
            "type": "function_pointer",
            "caller": caller,
            "callee": callee,
            "info": info
        })

    return relations


def get_mock_indirect_callees(caller: str) -> list:
    """
    获取某个函数的所有 mock 间接调用目标

    TODO: 等图谱修复后删除此函数

    Args:
        caller: 调用者函数名

    Returns:
        [(callee, bridge_info), ...] 列表
    """
    indirect_callees = []

    # 检查异步调用
    for (c, callee), info in MOCK_ASYNC_CALLS.items():
        if c == caller:
            indirect_callees.append((callee, info))

    # 检查函数指针
    for (c, callee), info in MOCK_FUNCTION_POINTER_CALLS.items():
        if c == caller:
            indirect_callees.append((callee, info))

    return indirect_callees

