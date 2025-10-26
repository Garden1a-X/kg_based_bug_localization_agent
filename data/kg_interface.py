"""
知识图谱接口模块
从JSON文件读取知识图谱数据
"""
import json
import os
from typing import Dict, List, Optional, Any
from loguru import logger
from pathlib import Path

# ============================================================
# TODO: 等图谱修复后删除这个导入
# ============================================================
from data.mock_indirect_calls import (
    get_mock_async_bridge,
    get_mock_function_pointer_bridge,
    get_mock_indirect_callees
)


class KnowledgeGraphInterface:
    """知识图谱接口 - 基于JSON文件"""

    def __init__(self, data_dir: str = None):
        """
        初始化知识图谱接口

        Args:
            data_dir: 数据文件所在目录
        """
        if data_dir is None:
            data_dir = os.getenv('KG_DATA_DIR', '/data/xuao/code_kg_search/linux_test/data')

        self.data_dir = Path(data_dir)

        # 缓存数据
        self.entities = {}  # {entity_type: {name: entity}}
        self.relations = {}  # {rel_type: [relations]}
        self.entity_by_id = {}  # {id: entity} - 用于通过id快速查找

        # 声明-实现映射
        self.decl_to_impl = {}  # {decl_id: impl_id}
        self.impl_to_decl = {}  # {impl_id: [decl_ids]}

        # 加载所有数据
        self._load_all_data()

        logger.info(f"已加载知识图谱: {data_dir}")
    
    def _load_all_data(self):
        """加载所有JSON文件"""
        logger.info("正在加载数据...")

        # 检查是否使用合并格式（temp_en.json + relations.json）
        entity_file = self.data_dir / 'temp_en.json'
        relation_file = self.data_dir / 'relations.json'

        if entity_file.exists() and relation_file.exists():
            logger.info("检测到合并格式数据文件")
            self._load_merged_format(entity_file, relation_file)
        else:
            logger.info("使用分散格式数据文件")
            self._load_separated_format()

    def _load_merged_format(self, entity_file: Path, relation_file: Path):
        """加载合并格式的数据（temp_en.json + relations.json）"""
        # 加载实体
        logger.info(f"加载实体文件: {entity_file.name}")
        with open(entity_file, 'r', encoding='utf-8') as f:
            entities_data = json.load(f)

        # 解析实体数据结构
        if isinstance(entities_data, dict):
            # 字典格式：按类型分组
            for entity_type, entity_list in entities_data.items():
                if isinstance(entity_list, list):
                    self.entities[entity_type] = {}
                    for item in entity_list:
                        if isinstance(item, dict) and 'name' in item:
                            self.entities[entity_type][item['name']] = item
                            # 同时建立 id 映射
                            if 'id' in item:
                                self.entity_by_id[item['id']] = item
                    logger.info(f"  ✓ 加载 {entity_type}: {len(self.entities[entity_type])} 个")
        elif isinstance(entities_data, list):
            # 列表格式：根据 type 字段分组（你的格式）
            for entity in entities_data:
                if isinstance(entity, dict) and 'name' in entity:
                    entity_type = entity.get('type', entity.get('entity_type', 'Unknown'))
                    if entity_type not in self.entities:
                        self.entities[entity_type] = {}
                    self.entities[entity_type][entity['name']] = entity
                    # 同时建立 id 映射
                    if 'id' in entity:
                        self.entity_by_id[entity['id']] = entity

            for entity_type, entities in self.entities.items():
                logger.info(f"  ✓ 加载 {entity_type}: {len(entities)} 个")

        # 建立声明-实现映射（针对函数）
        if 'FUNCTION' in self.entities:
            self._build_decl_impl_mapping()

        # 加载关系
        logger.info(f"加载关系文件: {relation_file.name}")
        with open(relation_file, 'r', encoding='utf-8') as f:
            relations_data = json.load(f)

        # 解析关系数据结构
        if isinstance(relations_data, dict):
            # 字典格式：按类型分组
            for rel_type, rel_list in relations_data.items():
                if isinstance(rel_list, list):
                    self.relations[rel_type] = rel_list
                    logger.info(f"  ✓ 加载 {rel_type}: {len(rel_list)} 个")
        elif isinstance(relations_data, list):
            # 列表格式：根据 type 字段分组
            for relation in relations_data:
                if isinstance(relation, dict):
                    rel_type = relation.get('type', relation.get('relation_type', 'UNKNOWN'))
                    if rel_type not in self.relations:
                        self.relations[rel_type] = []
                    self.relations[rel_type].append(relation)

            for rel_type, relations in self.relations.items():
                logger.info(f"  ✓ 加载 {rel_type}: {len(relations)} 个")

    def _build_decl_impl_mapping(self):
        """建立函数声明-实现映射"""
        from collections import defaultdict

        func_by_name = defaultdict(lambda: {'decls': [], 'impls': []})

        # 按名称分组，区分声明和实现
        for func_name, func_entity in self.entities['FUNCTION'].items():
            func_id = func_entity.get('id')
            is_decl = func_entity.get('is_declaration', False)

            if is_decl:
                func_by_name[func_name]['decls'].append(func_id)
            else:
                func_by_name[func_name]['impls'].append(func_id)

        # 建立映射关系
        mapping_count = 0
        for func_name, ids in func_by_name.items():
            decls = ids['decls']
            impls = ids['impls']

            # 如果有实现，将所有声明映射到第一个实现
            if impls:
                impl_id = impls[0]
                for decl_id in decls:
                    self.decl_to_impl[decl_id] = impl_id
                    if impl_id not in self.impl_to_decl:
                        self.impl_to_decl[impl_id] = []
                    self.impl_to_decl[impl_id].append(decl_id)
                    mapping_count += 1

        if mapping_count > 0:
            logger.info(f"  ✓ 建立声明→实现映射: {mapping_count} 对")

    def normalize_id(self, func_id):
        """
        标准化为实现ID

        Args:
            func_id: 函数ID（可能是声明或实现）

        Returns:
            实现ID
        """
        return self.decl_to_impl.get(func_id, func_id)

    def get_equivalent_ids(self, func_id):
        """
        获取等价ID集合（包括声明和实现）

        Args:
            func_id: 函数ID

        Returns:
            等价ID集合
        """
        equivalent = {func_id}

        # 如果是声明，添加对应的实现
        if func_id in self.decl_to_impl:
            equivalent.add(self.decl_to_impl[func_id])

        # 如果是实现，添加所有对应的声明
        if func_id in self.impl_to_decl:
            equivalent.update(self.impl_to_decl[func_id])

        return equivalent

    def _load_separated_format(self):
        """加载分散格式的数据（多个独立文件）"""
        # 加载实体
        entity_files = {
            'Function': 'entity_function.json',
            'Struct': 'entity_struct.json',
            'Variable': 'entity_variable.json',
            'Field': 'entity_field.json',
            'File': 'entity_file.json',
        }

        for entity_type, filename in entity_files.items():
            filepath = self.data_dir / filename
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
            filepath = self.data_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        data = list(data.values())
                    self.relations[rel_type] = data
                logger.info(f"✓ 加载 {rel_type}: {len(self.relations[rel_type])} 个")
    
    def close(self):
        """关闭连接"""
        logger.info("知识图谱接口关闭")
    
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
        if 'FUNCTION' not in self.entities:
            return None

        entity = self.entities['FUNCTION'].get(func_name)
        if entity and 'file' not in entity and 'source_file' in entity:
            # 添加 file 字段作为 source_file 的别名，保持向后兼容
            entity = entity.copy()
            entity['file'] = entity['source_file']

        return entity
    
    def find_functions_by_pattern(self, pattern: str) -> List[Dict]:
        """
        模糊查找函数

        Args:
            pattern: 函数名模式

        Returns:
            匹配的函数列表
        """
        if 'FUNCTION' not in self.entities:
            return []

        results = []
        for name, func in self.entities['FUNCTION'].items():
            if pattern.lower() in name.lower():
                # 添加 file 字段
                func_copy = func.copy()
                if 'file' not in func_copy and 'source_file' in func_copy:
                    func_copy['file'] = func_copy['source_file']
                results.append(func_copy)
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

        # 先获取两个函数的实体（带id）
        caller_entity = self.find_function(caller)
        callee_entity = self.find_function(callee)

        if not caller_entity or not callee_entity:
            return False

        caller_id = caller_entity.get('id')
        callee_id = callee_entity.get('id')

        if not caller_id or not callee_id:
            return False

        for rel in self.relations['CALLS']:
            # 关系中使用 head/tail 字段，存储的是 id
            head = rel.get('head')
            tail = rel.get('tail')

            if head == caller_id and tail == callee_id:
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

        # 获取起点和终点的实体（带id）
        start_entity = self.find_function(start)
        end_entity = self.find_function(end)

        if not start_entity or not end_entity:
            return None

        start_id = start_entity.get('id')
        end_id = end_entity.get('id')

        if not start_id or not end_id:
            return None

        # 构建邻接表（使用id）
        graph = {}
        for rel in self.relations['CALLS']:
            head = rel.get('head')  # caller id
            tail = rel.get('tail')  # callee id

            if head and tail:
                if head not in graph:
                    graph[head] = []
                graph[head].append(tail)

        # BFS搜索（使用id）
        from collections import deque

        queue = deque([(start_id, [start_id])])
        visited = {start_id}

        while queue:
            current_id, path_ids = queue.popleft()

            if len(path_ids) > max_depth:
                continue

            if current_id == end_id:
                # 将id路径转换为名字路径
                path_names = []
                for entity_id in path_ids:
                    entity = self.entity_by_id.get(entity_id)
                    if entity:
                        path_names.append(entity['name'])
                return path_names

            if current_id in graph:
                for neighbor_id in graph[current_id]:
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        queue.append((neighbor_id, path_ids + [neighbor_id]))

        return None

    def _find_indirect_callees(self, func_name: str) -> List[tuple]:
        """
        查找函数的间接调用目标

        Args:
            func_name: 函数名

        Returns:
            间接调用列表，每项为 (目标函数名, 桥接信息)
        """
        indirect_calls = []

        # ============================================================
        # TODO: 等图谱修复后，这里应该查询 ASSIGNED_TO 关系
        # 目前使用 mock 数据进行高效查询
        # ============================================================
        mock_callees = get_mock_indirect_callees(func_name)
        if mock_callees:
            logger.debug(f"函数 {func_name} 有 {len(mock_callees)} 个 mock 间接调用")
            return mock_callees

        # 如果图谱有 ASSIGNED_TO 关系，在这里查询
        # TODO: 实现基于 ASSIGNED_TO 关系的查询
        # if 'ASSIGNED_TO' in self.relations:
        #     for rel in self.relations['ASSIGNED_TO']:
        #         if matches_async_or_fp_pattern(rel, func_name):
        #             indirect_calls.append(...)

        return indirect_calls

    def find_call_path_with_indirect(self, start: str, end: str, max_depth: int = 10, debug: bool = False) -> Optional[Dict]:
        """
        查找调用路径（支持间接调用）

        Args:
            start: 起始函数名
            end: 目标函数名
            max_depth: 最大搜索深度
            debug: 是否输出调试信息

        Returns:
            包含路径和边类型信息的字典，如果不存在返回None
            {
                'path': [函数名列表],
                'edges': [边类型列表], # 'direct' 或 {'type': 'indirect', 'bridge': ...}
            }
        """
        if debug:
            print(f"\n{'='*80}")
            print(f"🔍 开始扩展BFS搜索")
            print(f"{'='*80}")
            print(f"起点: {start}")
            print(f"终点: {end}")
            print(f"最大深度: {max_depth}")

        # 获取起点和终点的实体
        start_entity = self.find_function(start)
        end_entity = self.find_function(end)

        if not start_entity or not end_entity:
            if debug:
                print(f"❌ 起点或终点不存在!")
                print(f"   起点存在: {start_entity is not None}")
                print(f"   终点存在: {end_entity is not None}")
            return None

        start_id = start_entity.get('id')
        end_id = end_entity.get('id')

        if not start_id or not end_id:
            if debug:
                print(f"❌ 起点或终点没有ID!")
                print(f"   start_id: {start_id}")
                print(f"   end_id: {end_id}")
            return None

        # 标准化为实现ID
        orig_start_id = start_id
        orig_end_id = end_id
        start_id = self.normalize_id(start_id)
        end_id = self.normalize_id(end_id)

        if debug:
            print(f"\n📌 ID信息:")
            print(f"   起点ID: {orig_start_id} -> {start_id}")
            print(f"   终点ID: {orig_end_id} -> {end_id}")

        # 获取终点的等价ID集合
        end_equivalent_ids = self.get_equivalent_ids(end_id)
        if debug:
            print(f"   终点等价ID: {end_equivalent_ids}")
            print()

        # BFS搜索（支持间接调用）
        from collections import deque

        queue = deque([(start_id, [start_id], [])])  # (当前id, 路径ids, 边类型)
        visited = {start_id}

        nodes_explored = 0
        max_queue_size = 0

        while queue:
            nodes_explored += 1
            max_queue_size = max(max_queue_size, len(queue))

            current_id, path_ids, edge_types = queue.popleft()

            if len(path_ids) > max_depth:
                continue

            # 检查是否到达终点（使用等价ID集合）
            if current_id in end_equivalent_ids:
                # 将id路径转换为名字路径
                path_names = []
                for entity_id in path_ids:
                    entity = self.entity_by_id.get(entity_id)
                    if entity:
                        path_names.append(entity['name'])

                if debug:
                    print(f"\n{'='*80}")
                    print(f"✅ 找到路径！")
                    print(f"{'='*80}")
                    print(f"📊 搜索统计:")
                    print(f"   总探索节点: {nodes_explored}")
                    print(f"   最大队列大小: {max_queue_size}")
                    print(f"   路径长度: {len(path_names)}")
                    print(f"{'='*80}\n")

                return {
                    'path': path_names,
                    'edges': edge_types
                }

            current_entity = self.entity_by_id.get(current_id)
            if not current_entity:
                continue

            current_name = current_entity['name']

            if debug and nodes_explored <= 20:  # 只输出前20个节点
                print(f"🔎 节点 #{nodes_explored}: {current_name} (深度 {len(path_ids)})")

            # 1. 获取直接调用的邻居
            direct_callees = self.get_callees(current_name)

            if debug and nodes_explored <= 20:
                print(f"   ├─ 直接调用: {len(direct_callees)} 个")

            for callee_name in direct_callees:
                callee_entity = self.find_function(callee_name)
                if not callee_entity:
                    continue

                callee_id = callee_entity.get('id')
                if not callee_id:
                    continue

                # 标准化ID
                callee_id = self.normalize_id(callee_id)
                if callee_id and callee_id not in visited:
                    visited.add(callee_id)
                    queue.append((
                        callee_id,
                        path_ids + [callee_id],
                        edge_types + ['direct']
                    ))

            # 2. 获取间接调用的邻居
            indirect_callees = self._find_indirect_callees(current_name)

            if debug and nodes_explored <= 20:
                print(f"   └─ 间接调用: {len(indirect_callees)} 个")
                if indirect_callees:
                    for callee_name, bridge_info in indirect_callees:
                        print(f"      ➜ {callee_name} ({bridge_info.get('bridge_type', 'unknown')})")

            for callee_name, bridge_info in indirect_callees:
                callee_entity = self.find_function(callee_name)
                if not callee_entity:
                    continue

                callee_id = callee_entity.get('id')
                if not callee_id:
                    continue

                # 标准化ID
                callee_id = self.normalize_id(callee_id)
                if callee_id and callee_id not in visited:
                    visited.add(callee_id)
                    queue.append((
                        callee_id,
                        path_ids + [callee_id],
                        edge_types + [{'type': 'indirect', 'bridge': bridge_info}]
                    ))

        # 搜索失败
        if debug:
            print(f"\n{'='*80}")
            print(f"❌ 搜索失败，未找到路径")
            print(f"{'='*80}")
            print(f"📊 搜索统计:")
            print(f"   总探索节点: {nodes_explored}")
            print(f"   最大队列大小: {max_queue_size}")
            print(f"   访问节点总数: {len(visited)}")
            print(f"{'='*80}\n")

        return None

    def find_reachable_from_start(self, start: str, max_depth: int = 10) -> Dict[str, List[str]]:
        """
        从起点出发，找到所有可达的函数及其路径

        Args:
            start: 起始函数名
            max_depth: 最大搜索深度

        Returns:
            {函数名: 到达该函数的路径}
        """
        start_entity = self.find_function(start)
        if not start_entity:
            return {}

        start_id = start_entity.get('id')
        if not start_id:
            return {}

        from collections import deque

        reachable = {start: [start]}
        queue = deque([(start_id, [start_id])])
        visited = {start_id}

        while queue:
            current_id, path_ids = queue.popleft()

            if len(path_ids) > max_depth:
                continue

            current_entity = self.entity_by_id.get(current_id)
            if not current_entity:
                continue

            current_name = current_entity['name']

            # 获取直接调用
            for callee_name in self.get_callees(current_name):
                callee_entity = self.find_function(callee_name)
                if not callee_entity:
                    continue

                callee_id = callee_entity.get('id')
                if callee_id and callee_id not in visited:
                    visited.add(callee_id)
                    new_path_ids = path_ids + [callee_id]
                    queue.append((callee_id, new_path_ids))

                    # 转换为名字路径
                    path_names = [self.entity_by_id[eid]['name'] for eid in new_path_ids if eid in self.entity_by_id]
                    reachable[callee_name] = path_names

        return reachable

    def find_reachable_to_end(self, end: str, max_depth: int = 10) -> Dict[str, List[str]]:
        """
        反向搜索：找到所有能到达终点的函数及其路径

        Args:
            end: 目标函数名
            max_depth: 最大搜索深度

        Returns:
            {函数名: 从该函数到终点的路径}
        """
        end_entity = self.find_function(end)
        if not end_entity:
            return {}

        end_id = end_entity.get('id')
        if not end_id:
            return {}

        from collections import deque

        reachable = {end: [end]}
        queue = deque([(end_id, [end_id])])
        visited = {end_id}

        while queue:
            current_id, path_ids = queue.popleft()

            if len(path_ids) > max_depth:
                continue

            current_entity = self.entity_by_id.get(current_id)
            if not current_entity:
                continue

            current_name = current_entity['name']

            # 获取调用者（反向）
            for caller_name in self.get_callers(current_name):
                caller_entity = self.find_function(caller_name)
                if not caller_entity:
                    continue

                caller_id = caller_entity.get('id')
                if caller_id and caller_id not in visited:
                    visited.add(caller_id)
                    new_path_ids = [caller_id] + path_ids
                    queue.append((caller_id, new_path_ids))

                    # 转换为名字路径
                    path_names = [self.entity_by_id[eid]['name'] for eid in new_path_ids if eid in self.entity_by_id]
                    reachable[caller_name] = path_names

        return reachable

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

        # 获取目标函数的实体（带id）
        func_entity = self.find_function(func_name)
        if not func_entity:
            return []

        func_id = func_entity.get('id')
        if not func_id:
            return []

        callers = []
        for rel in self.relations['CALLS']:
            head = rel.get('head')  # caller id
            tail = rel.get('tail')  # callee id

            if tail == func_id:
                # 通过 id 查找 caller 的名字
                caller_entity = self.entity_by_id.get(head)
                if caller_entity and 'name' in caller_entity:
                    callers.append(caller_entity['name'])

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

        # 获取函数的实体（带id）
        func_entity = self.find_function(func_name)
        if not func_entity:
            return []

        func_id = func_entity.get('id')
        if not func_id:
            return []

        callees = []
        for rel in self.relations['CALLS']:
            head = rel.get('head')  # caller id
            tail = rel.get('tail')  # callee id

            if head == func_id:
                # 通过 id 查找 callee 的名字
                callee_entity = self.entity_by_id.get(tail)
                if callee_entity and 'name' in callee_entity:
                    callees.append(callee_entity['name'])

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
        # 首先尝试从真实图谱中查找
        if 'ASSIGNED_TO' in self.relations:
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

        # ============================================================
        # TODO: 等图谱修复后删除这部分代码
        # 作为临时方案，使用 mock 数据
        # ============================================================
        mock_bridge = get_mock_async_bridge(node_a, node_b)
        if mock_bridge:
            logger.debug(f"使用 mock 异步调用桥接: {node_a} -> {node_b}")
            return mock_bridge

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
        # 首先尝试从真实图谱中查找
        if 'ASSIGNED_TO' in self.relations:
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

        # ============================================================
        # TODO: 等图谱修复后删除这部分代码
        # 作为临时方案，使用 mock 数据
        # ============================================================
        mock_bridge = get_mock_function_pointer_bridge(node_a, node_b)
        if mock_bridge:
            logger.debug(f"使用 mock 函数指针桥接: {node_a} -> {node_b}")
            return mock_bridge

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


# 便捷函数：创建知识图谱接口
def create_kg_interface(data_dir: str = None) -> KnowledgeGraphInterface:
    """
    创建知识图谱接口实例

    Args:
        data_dir: 数据文件目录，如果为None则从环境变量读取

    Returns:
        KnowledgeGraphInterface实例
    """
    return KnowledgeGraphInterface(data_dir)
