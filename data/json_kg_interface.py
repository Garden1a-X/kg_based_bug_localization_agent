"""
JSON知识图谱接口模块
直接从JSON文件读取知识图谱数据，不需要Neo4j
"""
import json
import os
from typing import Dict, List, Optional, Any
from loguru import logger
from pathlib import Path


class JSONGraphInterface:
    """从JSON文件读取的知识图谱接口"""
    
    def __init__(self, json_dir: str):
        """
        初始化JSON图谱接口
        
        Args:
            json_dir: JSON文件所在目录
        """
        self.json_dir = Path(json_dir)
        
        # 缓存数据
        self.entities = {}
        self.relations = {}
        
        # 加载所有数据
        self._load_all_data()
        
        logger.info(f"已从JSON加载图谱: {json_dir}")
    
    def _load_all_data(self):
        """加载所有JSON文件"""
        logger.info("正在加载JSON数据...")
        
        # 加载实体
        entity_files = {
            'Function': 'entity_function.json',
            'Struct': 'entity_struct.json',
            'Variable': 'entity_variable.json',
            'Field': 'entity_field.json',
            'File': 'entity_file.json',
        }
        
        for entity_type, filename in entity_files.items():
            filepath = self.json_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 如果是字典，转为列表
                    if isinstance(data, dict):
                        data = list(data.values())
                    self.entities[entity_type] = {
                        item['name']: item for item in data if 'name' in item
                    }
                logger.info(f"✓ 加载 {entity_type}: {len(self.entities[entity_type])} 个")
        
        # 加载关系
        relation_files = {
            'CALLS': 'relation_calls.json',
            'CONTAINS': 'relation_contains.json',
            'TYPE_OF': 'relation_typeof.json',
            'ASSIGNED_TO': 'relation_assignedto.json',
            'HAS_MEMBERS': 'relation_has_members.json',
            'RETURNS': 'relation_returns.json',
            'HAS_PARAMETERS': 'relation_has_parameters.json',
            'HAS_VARIABLES': 'relation_has_variables.json',
            'INCLUDES': 'relation_includes.json',
        }
        
        for rel_type, filename in relation_files.items():
            filepath = self.json_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        data = list(data.values())
                    self.relations[rel_type] = data
                logger.info(f"✓ 加载 {rel_type}: {len(self.relations[rel_type])} 个")
    
    def close(self):
        """关闭连接（JSON版本不需要，保持接口一致）"""
        logger.info("JSON图谱接口关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # ============ 基础查询方法 ============
    
    def query(self, cypher: str, **params) -> List[Dict]:
        """
        模拟Cypher查询（简化版本）
        注意：这是简化实现，不支持复杂的Cypher语法
        """
        # JSON版本不需要Cypher，直接返回空
        logger.warning("JSON模式不支持直接Cypher查询，请使用专用方法")
        return []
    
    def entity_exists(self, entity_type: str, name: str) -> bool:
        """
        检查实体是否存在
        
        Args:
            entity_type: 实体类型（Function, Struct, Variable等）
            name: 实体名称
            
        Returns:
            是否存在
        """
        if entity_type not in self.entities:
            return False
        return name in self.entities[entity_type]
    
    # ============ 函数相关查询 ============
    
    def find_function(self, func_name: str) -> Optional[Dict]:
        """
        查找函数实体
        
        Args:
            func_name: 函数名
            
        Returns:
            函数实体信息，如果不存在返回None
        """
        if 'Function' not in self.entities:
            return None
        
        return self.entities['Function'].get(func_name)
    
    def find_functions_by_pattern(self, pattern: str) -> List[Dict]:
        """
        模糊查找函数
        
        Args:
            pattern: 函数名模式
            
        Returns:
            匹配的函数列表
        """
        if 'Function' not in self.entities:
            return []
        
        results = []
        for name, func in self.entities['Function'].items():
            if pattern.lower() in name.lower():
                results.append(func)
                if len(results) >= 10:  # 限制返回数量
                    break
        
        return results
    
    def get_function_code(self, func_name: str) -> Optional[str]:
        """
        获取函数代码
        
        Args:
            func_name: 函数名
            
        Returns:
            函数代码字符串
        """
        func = self.find_function(func_name)
        if not func:
            return None
        
        return func.get('code') or func.get('body')
    
    # ============ 调用关系查询 ============
    
    def has_direct_call(self, caller: str, callee: str) -> bool:
        """
        检查两个函数之间是否有直接CALLS关系
        
        Args:
            caller: 调用者函数名
            callee: 被调用者函数名
            
        Returns:
            是否存在直接调用关系
        """
        if 'CALLS' not in self.relations:
            return False
        
        for rel in self.relations['CALLS']:
            src = rel.get('source') or rel.get('from') or rel.get('caller')
            tgt = rel.get('target') or rel.get('to') or rel.get('callee')
            
            if src == caller and tgt == callee:
                return True
        
        return False
    
    def find_call_path(self, start: str, end: str, max_depth: int = 10) -> Optional[List[str]]:
        """
        查找两个函数之间的调用路径（BFS搜索）
        
        Args:
            start: 起始函数名
            end: 目标函数名
            max_depth: 最大搜索深度
            
        Returns:
            调用路径（函数名列表），如果不存在返回None
        """
        if 'CALLS' not in self.relations:
            return None
        
        # 构建邻接表
        graph = {}
        for rel in self.relations['CALLS']:
            src = rel.get('source') or rel.get('from') or rel.get('caller')
            tgt = rel.get('target') or rel.get('to') or rel.get('callee')
            
            if src not in graph:
                graph[src] = []
            graph[src].append(tgt)
        
        # BFS搜索
        from collections import deque
        
        queue = deque([(start, [start])])
        visited = {start}
        
        while queue:
            current, path = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            if current == end:
                return path
            
            if current in graph:
                for neighbor in graph[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def get_all_paths(self, start: str, end: str, max_depth: int = 10, limit: int = 5) -> List[List[str]]:
        """
        获取所有可能的调用路径（DFS搜索）
        
        Args:
            start: 起始函数
            end: 目标函数
            max_depth: 最大深度
            limit: 最多返回路径数
            
        Returns:
            路径列表
        """
        if 'CALLS' not in self.relations:
            return []
        
        # 构建邻接表
        graph = {}
        for rel in self.relations['CALLS']:
            src = rel.get('source') or rel.get('from') or rel.get('caller')
            tgt = rel.get('target') or rel.get('to') or rel.get('callee')
            
            if src not in graph:
                graph[src] = []
            graph[src].append(tgt)
        
        # DFS查找所有路径
        all_paths = []
        
        def dfs(current, path, visited):
            if len(all_paths) >= limit:
                return
            
            if len(path) > max_depth:
                return
            
            if current == end:
                all_paths.append(path[:])
                return
            
            if current in graph:
                for neighbor in graph[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        path.append(neighbor)
                        dfs(neighbor, path, visited)
                        path.pop()
                        visited.remove(neighbor)
        
        dfs(start, [start], {start})
        
        return all_paths
    
    def get_callers(self, func_name: str) -> List[str]:
        """
        获取调用某函数的所有函数
        
        Args:
            func_name: 函数名
            
        Returns:
            调用者函数名列表
        """
        if 'CALLS' not in self.relations:
            return []
        
        callers = []
        for rel in self.relations['CALLS']:
            src = rel.get('source') or rel.get('from') or rel.get('caller')
            tgt = rel.get('target') or rel.get('to') or rel.get('callee')
            
            if tgt == func_name:
                callers.append(src)
        
        return list(set(callers))
    
    def get_callees(self, func_name: str) -> List[str]:
        """
        获取某函数调用的所有函数
        
        Args:
            func_name: 函数名
            
        Returns:
            被调用函数名列表
        """
        if 'CALLS' not in self.relations:
            return []
        
        callees = []
        for rel in self.relations['CALLS']:
            src = rel.get('source') or rel.get('from') or rel.get('caller')
            tgt = rel.get('target') or rel.get('to') or rel.get('callee')
            
            if src == func_name:
                callees.append(tgt)
        
        return list(set(callees))
    
    # ============ 断点修复相关查询 ============
    
    def check_async_pattern(self, node_a: str, node_b: str) -> Optional[Dict]:
        """
        检查异步调用模式（work_struct）
        
        Args:
            node_a: 起始函数
            node_b: 目标函数
            
        Returns:
            桥接信息，如果不存在返回None
        """
        if 'ASSIGNED_TO' not in self.relations:
            return None
        
        # 查找 work_struct.func 指向 node_b 的关系
        for rel in self.relations['ASSIGNED_TO']:
            src = rel.get('source') or rel.get('from')
            tgt = rel.get('target') or rel.get('to')
            
            # 检查是否是 work_struct 的 func 字段指向目标函数
            if tgt == node_b and 'func' in str(src).lower():
                return {
                    'bridge_type': 'async',
                    'bridge_entity': 'work_struct.func',
                    'init_func': 'INIT_WORK/INIT_DELAYED_WORK'
                }
        
        return None
    
    def check_function_pointer_pattern(self, node_a: str, node_b: str) -> Optional[Dict]:
        """
        检查函数指针调用模式（ops表）
        
        Args:
            node_a: 起始函数
            node_b: 目标函数
            
        Returns:
            桥接信息，如果不存在返回None
        """
        if 'ASSIGNED_TO' not in self.relations:
            return None
        
        # 查找 ops 相关的赋值
        for rel in self.relations['ASSIGNED_TO']:
            src = rel.get('source') or rel.get('from')
            tgt = rel.get('target') or rel.get('to')
            
            # 检查是否是 ops 表字段指向目标函数
            if tgt == node_b and 'ops' in str(src).lower():
                return {
                    'bridge_type': 'function_pointer',
                    'bridge_entity': src,
                    'ops_var': src
                }
        
        return None
    
    # ============ 上下文查询 ============
    
    def get_function_context(self, func_name: str) -> Dict[str, Any]:
        """
        获取函数的完整上下文信息
        
        Args:
            func_name: 函数名
            
        Returns:
            包含函数所有相关信息的字典
        """
        func_info = self.find_function(func_name)
        if not func_info:
            return {}
        
        return {
            'info': func_info,
            'code': self.get_function_code(func_name),
            'callers': self.get_callers(func_name),
            'callees': self.get_callees(func_name),
            'variables': self.get_function_variables(func_name),
            'related_structs': self.get_related_structs(func_name)
        }
    
    def get_function_variables(self, func_name: str) -> List[Dict]:
        """获取函数中使用的变量"""
        if 'CONTAINS' not in self.relations:
            return []
        
        variables = []
        for rel in self.relations['CONTAINS']:
            src = rel.get('source') or rel.get('from')
            tgt = rel.get('target') or rel.get('to')
            
            if src == func_name and 'Variable' in self.entities:
                var_info = self.entities['Variable'].get(tgt)
                if var_info:
                    variables.append(var_info)
        
        return variables
    
    def get_related_structs(self, func_name: str) -> List[str]:
        """获取函数相关的结构体"""
        variables = self.get_function_variables(func_name)
        
        if 'TYPE_OF' not in self.relations:
            return []
        
        struct_names = set()
        for var in variables:
            var_name = var.get('name')
            for rel in self.relations['TYPE_OF']:
                src = rel.get('source') or rel.get('from')
                tgt = rel.get('target') or rel.get('to')
                
                if src == var_name:
                    struct_names.add(tgt)
        
        return list(struct_names)
    
    # ============ 统计信息 ============
    
    def get_call_frequency(self, func_name: str) -> int:
        """获取函数被调用的次数"""
        return len(self.get_callers(func_name))
    
    def get_database_stats(self) -> Dict[str, int]:
        """获取图谱统计信息"""
        stats = {}
        
        # 统计实体
        for entity_type, entities in self.entities.items():
            stats[entity_type] = len(entities)
        
        # 统计关系
        for rel_type, relations in self.relations.items():
            stats[rel_type] = len(relations)
        
        return stats


# 便捷函数：创建JSON图谱接口
def create_json_graph_interface(json_dir: str = None) -> JSONGraphInterface:
    """
    创建JSON图谱接口实例
    
    Args:
        json_dir: JSON文件目录，如果为None则从配置读取
        
    Returns:
        JSONGraphInterface实例
    """
    if json_dir is None:
        # 从环境变量或配置读取
        json_dir = os.getenv('JSON_GRAPH_DIR', '/data/xuao/code_kg_search/linux_test')
    
    return JSONGraphInterface(json_dir)
