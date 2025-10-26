"""
调用链追踪Agent
构建从入口到错误点的完整调用链
实现分层降级策略：图谱 -> 规则 -> LLM
"""
from typing import List, Optional, Dict, Tuple
from agents.base_agent import BaseAgent
from data.kg_interface import KnowledgeGraphInterface


class CallChainTracerAgent(BaseAgent):
    """调用链追踪Agent - 分层降级策略"""
    
    def __init__(self, kg: KnowledgeGraphInterface, llm_client=None):
        super().__init__("CallChainTracer")
        self.kg = kg
        self.llm = llm_client  # 可选的LLM客户端
        
        # 统计信息
        self.stats = {
            'total_breaks': 0,
            'fixed_by_rules': 0,
            'fixed_by_llm': 0,
            'unfixed': 0
        }
    
    def execute(self, start_entity: Dict, end_entity: Dict, 
                max_depth: int = 15) -> Dict:
        """
        追踪调用链
        
        Args:
            start_entity: 起始实体
            end_entity: 目标实体
            max_depth: 最大搜索深度
            
        Returns:
            调用链信息
        """
        start_name = start_entity['name']
        end_name = end_entity['name']
        
        self.log_start(f"追踪调用链: {start_name} -> {end_name}")
        
        # 1. 尝试在图谱中查找路径
        path = self.kg.find_call_path(start_name, end_name, max_depth)
        
        if not path:
            self.log_error("图谱中未找到直接调用路径")
            return {
                'path': [],
                'breaks': [],
                'stats': self.stats,
                'success': False
            }
        
        self.log_success(f"找到初始路径，长度: {len(path)}")
        
        # 2. 检测断点
        breaks = self._detect_breaks(path)
        
        if not breaks:
            self.log_success("路径完整，无断点")
            return {
                'path': path,
                'breaks': [],
                'stats': self.stats,
                'success': True
            }
        
        self.log_warning(f"检测到 {len(breaks)} 个断点")
        self.stats['total_breaks'] = len(breaks)
        
        # 3. 修复断点
        fixed_path, fixed_breaks = self._fix_breaks(path, breaks)
        
        # 4. 返回结果
        return {
            'path': fixed_path,
            'breaks': fixed_breaks,
            'stats': self.stats,
            'success': len([b for b in fixed_breaks if not b['fixed']]) == 0
        }
    
    def _detect_breaks(self, path: List[str]) -> List[Tuple[int, str, str]]:
        """
        检测路径中的断点
        
        Args:
            path: 函数调用路径
            
        Returns:
            断点列表，每个断点是 (位置, 函数A, 函数B) 的元组
        """
        breaks = []
        
        for i in range(len(path) - 1):
            node_a = path[i]
            node_b = path[i + 1]
            
            if not self.kg.has_direct_call(node_a, node_b):
                breaks.append((i, node_a, node_b))
                self.log_warning(f"断点 {i+1}: {node_a} -/-> {node_b}")
        
        return breaks
    
    def _fix_breaks(self, path: List[str], breaks: List[Tuple[int, str, str]]) -> Tuple[List[str], List[Dict]]:
        """
        修复所有断点
        
        Args:
            path: 原始路径
            breaks: 断点列表
            
        Returns:
            (修复后的路径, 断点修复信息列表)
        """
        fixed_path = path.copy()
        fixed_breaks = []
        
        # 按位置倒序修复（避免插入位置变化）
        for pos, node_a, node_b in reversed(breaks):
            self.log_info(f"尝试修复断点: {node_a} -> {node_b}")
            
            fix_result = self._fix_break_with_fallback(node_a, node_b)
            
            break_info = {
                'position': pos,
                'from': node_a,
                'to': node_b,
                'fixed': fix_result is not None,
                'method': fix_result[0] if fix_result else None,
                'bridge': fix_result[1] if fix_result else None
            }
            
            if fix_result:
                method, bridge = fix_result
                # 插入桥接实体到路径中
                if isinstance(bridge, str):
                    fixed_path.insert(pos + 1, bridge)
                elif isinstance(bridge, dict) and 'entity' in bridge:
                    fixed_path.insert(pos + 1, bridge['entity'])
                
                self.log_success(f"✓ 通过{method}修复成功")
            else:
                self.log_error(f"✗ 无法修复")
            
            fixed_breaks.append(break_info)
        
        # 倒序遍历，所以最后要反转
        fixed_breaks.reverse()
        
        return fixed_path, fixed_breaks
    
    def _fix_break_with_fallback(self, node_a: str, node_b: str) -> Optional[Tuple[str, any]]:
        """
        分层降级修复断点
        
        Args:
            node_a: 起始函数
            node_b: 目标函数
            
        Returns:
            (修复方法, 桥接信息) 或 None
        """
        # === 第1层：尝试专家规则 ===
        self.log_info("第1层：尝试专家规则...")
        bridge = self._try_expert_rules(node_a, node_b)
        
        if bridge:
            self.stats['fixed_by_rules'] += 1
            return ('rule', bridge)
        
        # === 第2层：LLM兜底 ===
        if self.llm:
            self.log_warning("第2层：规则失败，启用LLM推理...")
            bridge = self._llm_infer_bridge(node_a, node_b)
            
            if bridge and bridge.get('confidence', 0) > 0.6:
                self.stats['fixed_by_llm'] += 1
                return ('llm', bridge)
        
        # === 第3层：无法修复 ===
        self.log_error("第3层：无法修复此断点")
        self.stats['unfixed'] += 1
        return None
    
    def _try_expert_rules(self, node_a: str, node_b: str) -> Optional[Dict]:
        """
        尝试所有专家规则
        
        Args:
            node_a: 起始函数
            node_b: 目标函数
            
        Returns:
            桥接信息或None
        """
        # 规则1: 异步调用
        bridge = self._check_async_pattern(node_a, node_b)
        if bridge:
            return bridge
        
        # 规则2: 函数指针
        bridge = self._check_function_pointer_pattern(node_a, node_b)
        if bridge:
            return bridge
        
        # 规则3: 回调注册（待实现）
        # bridge = self._check_callback_pattern(node_a, node_b)
        # if bridge: return bridge
        
        # 规则4: 事件触发（待实现）
        # bridge = self._check_event_pattern(node_a, node_b)
        # if bridge: return bridge
        
        return None
    
    def _check_async_pattern(self, node_a: str, node_b: str) -> Optional[Dict]:
        """
        规则1: 检查异步调用模式（work_struct）
        
        Args:
            node_a: 起始函数
            node_b: 目标函数
            
        Returns:
            桥接信息或None
        """
        result = self.kg.check_async_pattern(node_a, node_b)
        
        if result:
            self.log_success(f"✓ 检测到异步调用: {result.get('init_func')}")
            return result
        
        return None
    
    def _check_function_pointer_pattern(self, node_a: str, node_b: str) -> Optional[Dict]:
        """
        规则2: 检查函数指针调用模式（ops表）
        
        Args:
            node_a: 起始函数
            node_b: 目标函数
            
        Returns:
            桥接信息或None
        """
        result = self.kg.check_function_pointer_pattern(node_a, node_b)
        
        if result:
            self.log_success(f"✓ 检测到函数指针: {result.get('struct_name')}.{result.get('field_name')}")
            return result
        
        return None
    
    def _llm_infer_bridge(self, node_a: str, node_b: str) -> Optional[Dict]:
        """
        LLM推理：当所有规则都失败时
        
        Args:
            node_a: 起始函数
            node_b: 目标函数
            
        Returns:
            桥接信息或None
        """
        if not self.llm:
            return None
        
        # 1. 收集上下文
        context = self._collect_bridge_context(node_a, node_b)
        
        # 2. 构建提示词
        prompt = self._build_bridge_inference_prompt(node_a, node_b, context)
        
        # 3. 调用LLM
        try:
            response = self.llm.complete(prompt)
            result = self._parse_llm_response(response)
            return result
        except Exception as e:
            self.log_error(f"LLM推理失败: {e}")
            return None
    
    def _collect_bridge_context(self, node_a: str, node_b: str) -> Dict:
        """收集用于LLM推理的上下文"""
        return {
            'code_a': self.kg.get_function_code(node_a) or "代码未找到",
            'code_b': self.kg.get_function_code(node_b) or "代码未找到",
            'callees_a': self.kg.get_callees(node_a),
            'callers_b': self.kg.get_callers(node_b),
            'related_structs_a': self.kg.get_related_structs(node_a),
            'related_structs_b': self.kg.get_related_structs(node_b)
        }
    
    def _build_bridge_inference_prompt(self, node_a: str, node_b: str, context: Dict) -> str:
        """构建LLM推理提示词"""
        prompt = f"""
# 任务：推理函数调用关系

## 已知信息
- 函数A: {node_a}
- 函数B: {node_b}
- 函数A调用的其他函数: {context['callees_a']}
- 调用函数B的其他函数: {context['callers_b']}
- 函数A相关的结构体: {context['related_structs_a']}
- 函数B相关的结构体: {context['related_structs_b']}

## 函数A的代码片段
```c
{context['code_a'][:500]}  // 截取前500字符
```

## 函数B的代码片段
```c
{context['code_b'][:500]}  // 截取前500字符
```

## 问题
在调用链中，函数A和函数B之间缺少直接的CALLS关系。
请分析可能存在的间接调用机制，包括但不限于：
1. 异步调用（工作队列、定时器）
2. 函数指针/回调函数
3. 事件驱动/中断
4. 其他间接调用方式

请返回JSON格式：
{{
    "bridge_type": "async|function_pointer|callback|event|unknown",
    "entity": "中间实体名称",
    "confidence": 0.0-1.0,
    "explanation": "推理依据"
}}
"""
        return prompt
    
    def _parse_llm_response(self, response: str) -> Optional[Dict]:
        """解析LLM响应"""
        # 简化处理，实际应该更健壮
        import json
        try:
            # 去除markdown代码块标记
            response = response.replace('```json', '').replace('```', '').strip()
            result = json.loads(response)
            return result
        except:
            return None
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()
