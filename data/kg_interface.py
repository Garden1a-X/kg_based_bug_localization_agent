"""
知识图谱接口模块
提供与Neo4j图数据库交互的所有方法
"""
from neo4j import GraphDatabase
from typing import Dict, List, Optional, Any
from loguru import logger


class KnowledgeGraphInterface:
    """知识图谱查询接口"""
    
    def __init__(self, uri: str, user: str, password: str):
        """
        初始化Neo4j连接
        
        Args:
            uri: Neo4j连接URI
            user: 用户名
            password: 密码
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"已连接到Neo4j: {uri}")
    
    def close(self):
        """关闭连接"""
        self.driver.close()
        logger.info("已关闭Neo4j连接")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # ============ 基础查询方法 ============
    
    def query(self, cypher: str, **params) -> List[Dict]:
        """
        执行Cypher查询
        
        Args:
            cypher: Cypher查询语句
            **params: 查询参数
            
        Returns:
            查询结果列表
        """
        with self.driver.session() as session:
            result = session.run(cypher, **params)
            return [dict(record) for record in result]
    
    def entity_exists(self, entity_type: str, name: str) -> bool:
        """
        检查实体是否存在
        
        Args:
            entity_type: 实体类型（Function, Struct, Variable等）
            name: 实体名称
            
        Returns:
            是否存在
        """
        cypher = f"MATCH (e:{entity_type} {{name: $name}}) RETURN count(e) > 0 as exists"
        result = self.query(cypher, name=name)
        return result[0]['exists'] if result else False
    
    # ============ 函数相关查询 ============
    
    def find_function(self, func_name: str) -> Optional[Dict]:
        """
        查找函数实体
        
        Args:
            func_name: 函数名
            
        Returns:
            函数实体信息，如果不存在返回None
        """
        cypher = """
        MATCH (f:Function {name: $name})
        RETURN f.name as name, 
               f.file as file,
               f.start_line as start_line,
               f.end_line as end_line
        """
        results = self.query(cypher, name=func_name)
        return results[0] if results else None
    
    def find_functions_by_pattern(self, pattern: str) -> List[Dict]:
        """
        模糊查找函数（用于处理宏展开等情况）
        
        Args:
            pattern: 函数名模式（支持正则）
            
        Returns:
            匹配的函数列表
        """
        cypher = """
        MATCH (f:Function)
        WHERE f.name =~ $pattern
        RETURN f.name as name, f.file as file
        LIMIT 10
        """
        return self.query(cypher, pattern=f".*{pattern}.*")
    
    def get_function_code(self, func_name: str) -> Optional[str]:
        """
        获取函数代码
        
        Args:
            func_name: 函数名
            
        Returns:
            函数代码字符串
        """
        func_info = self.find_function(func_name)
        if not func_info:
            return None
        
        # 从文件中读取代码（如果图谱中存储了代码路径）
        # 这里简化处理，实际可能需要读取源文件
        cypher = """
        MATCH (f:Function {name: $name})
        RETURN f.code as code
        """
        results = self.query(cypher, name=func_name)
        return results[0]['code'] if results and 'code' in results[0] else None
    
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
        cypher = """
        MATCH (a:Function {name: $caller})-[:CALLS]->(b:Function {name: $callee})
        RETURN count(*) > 0 as has_call
        """
        results = self.query(cypher, caller=caller, callee=callee)
        return results[0]['has_call'] if results else False
    
    def find_call_path(self, start: str, end: str, max_depth: int = 10) -> Optional[List[str]]:
        """
        查找两个函数之间的调用路径（只考虑CALLS关系）
        
        Args:
            start: 起始函数名
            end: 目标函数名
            max_depth: 最大搜索深度
            
        Returns:
            调用路径（函数名列表），如果不存在返回None
        """
        cypher = f"""
        MATCH path = (start:Function {{name: $start}})
                     -[:CALLS*1..{max_depth}]->
                     (end:Function {{name: $end}})
        RETURN [node in nodes(path) | node.name] as path
        ORDER BY length(path)
        LIMIT 1
        """
        results = self.query(cypher, start=start, end=end)
        return results[0]['path'] if results else None
    
    def get_all_paths(self, start: str, end: str, max_depth: int = 10, limit: int = 5) -> List[List[str]]:
        """
        获取所有可能的调用路径
        
        Args:
            start: 起始函数
            end: 目标函数
            max_depth: 最大深度
            limit: 最多返回路径数
            
        Returns:
            路径列表
        """
        cypher = f"""
        MATCH path = (start:Function {{name: $start}})
                     -[:CALLS*1..{max_depth}]->
                     (end:Function {{name: $end}})
        RETURN [node in nodes(path) | node.name] as path
        ORDER BY length(path)
        LIMIT {limit}
        """
        results = self.query(cypher, start=start, end=end)
        return [r['path'] for r in results]
    
    def get_callers(self, func_name: str) -> List[str]:
        """
        获取调用某函数的所有函数
        
        Args:
            func_name: 函数名
            
        Returns:
            调用者函数名列表
        """
        cypher = """
        MATCH (caller:Function)-[:CALLS]->(f:Function {name: $name})
        RETURN caller.name as name
        """
        results = self.query(cypher, name=func_name)
        return [r['name'] for r in results]
    
    def get_callees(self, func_name: str) -> List[str]:
        """
        获取某函数调用的所有函数
        
        Args:
            func_name: 函数名
            
        Returns:
            被调用函数名列表
        """
        cypher = """
        MATCH (f:Function {name: $name})-[:CALLS]->(callee:Function)
        RETURN callee.name as name
        """
        results = self.query(cypher, name=func_name)
        return [r['name'] for r in results]
    
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
        # 查找 node_a 是否调用了 INIT_WORK/INIT_DELAYED_WORK
        cypher = """
        MATCH (a:Function {name: $node_a})-[:CALLS]->(init:Function)
        WHERE init.name IN ['INIT_WORK', 'INIT_DELAYED_WORK', 
                           'INIT_DEFERRABLE_WORK', '__INIT_WORK']
        MATCH (ws:Struct {name: 'work_struct'})-[:HAS_MEMBERS]->(func:Field {name: 'func'})
        MATCH (func)-[:ASSIGNED_TO]->(b:Function {name: $node_b})
        RETURN 'async' as bridge_type, 
               init.name as init_func,
               'work_struct.func' as bridge_entity
        """
        results = self.query(cypher, node_a=node_a, node_b=node_b)
        return results[0] if results else None
    
    def check_function_pointer_pattern(self, node_a: str, node_b: str) -> Optional[Dict]:
        """
        检查函数指针调用模式（ops表）
        
        Args:
            node_a: 起始函数
            node_b: 目标函数
            
        Returns:
            桥接信息，如果不存在返回None
        """
        # 查找 node_a 中访问的 ops 相关变量
        cypher = """
        MATCH (a:Function {name: $node_a})-[:CONTAINS]->(var:Variable)
        WHERE var.name ENDS WITH 'ops' OR var.name CONTAINS '_ops'
        MATCH (var)-[:TYPE_OF]->(opsType:Struct)
        MATCH (opsType)-[:HAS_MEMBERS]->(field:Field)
        MATCH (field)-[:ASSIGNED_TO]->(b:Function {name: $node_b})
        RETURN 'function_pointer' as bridge_type,
               var.name as ops_var,
               field.name as field_name,
               opsType.name as struct_name
        """
        results = self.query(cypher, node_a=node_a, node_b=node_b)
        return results[0] if results else None
    
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
        cypher = """
        MATCH (f:Function {name: $name})-[:CONTAINS]->(v:Variable)
        RETURN v.name as name, v.type as type
        """
        return self.query(cypher, name=func_name)
    
    def get_related_structs(self, func_name: str) -> List[str]:
        """获取函数相关的结构体"""
        cypher = """
        MATCH (f:Function {name: $name})-[:CONTAINS]->(v:Variable)
        MATCH (v)-[:TYPE_OF]->(s:Struct)
        RETURN DISTINCT s.name as name
        """
        results = self.query(cypher, name=func_name)
        return [r['name'] for r in results]
    
    # ============ 统计信息 ============
    
    def get_call_frequency(self, func_name: str) -> int:
        """获取函数被调用的次数"""
        cypher = """
        MATCH (:Function)-[:CALLS]->(f:Function {name: $name})
        RETURN count(*) as frequency
        """
        results = self.query(cypher, name=func_name)
        return results[0]['frequency'] if results else 0
    
    def get_database_stats(self) -> Dict[str, int]:
        """获取图谱统计信息"""
        stats = {}
        
        # 统计各类实体数量
        for entity_type in ['Function', 'Struct', 'Variable', 'Field', 'File']:
            cypher = f"MATCH (e:{entity_type}) RETURN count(e) as count"
            result = self.query(cypher)
            stats[entity_type] = result[0]['count'] if result else 0
        
        # 统计各类关系数量
        for rel_type in ['CALLS', 'CONTAINS', 'TYPE_OF', 'ASSIGNED_TO', 'HAS_MEMBERS']:
            cypher = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            result = self.query(cypher)
            stats[rel_type] = result[0]['count'] if result else 0
        
        return stats


# 便捷函数：创建KG接口
def create_kg_interface(uri: str = None, user: str = None, password: str = None) -> KnowledgeGraphInterface:
    """
    创建知识图谱接口实例
    
    Args:
        uri: Neo4j URI，如果为None则从配置读取
        user: 用户名，如果为None则从配置读取
        password: 密码，如果为None则从配置读取
        
    Returns:
        KnowledgeGraphInterface实例
    """
    # 如果没有提供参数，从配置文件读取
    if uri is None or user is None or password is None:
        try:
            from config.settings import settings
            uri = uri or settings.neo4j_uri
            user = user or settings.neo4j_user
            password = password or settings.neo4j_password
        except ImportError:
            raise ValueError("必须提供Neo4j连接参数或配置settings模块")
    
    return KnowledgeGraphInterface(uri, user, password)
