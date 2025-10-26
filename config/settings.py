"""
配置管理模块
使用pydantic管理所有配置
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """全局配置"""
    
    # Neo4j配置
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    # Anthropic配置
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-20250514"
    
    # LLM配置
    llm_max_tokens: int = 4000
    llm_temperature: float = 0.0
    llm_confidence_threshold: float = 0.6
    
    # 调用链配置
    max_chain_depth: int = 15
    max_breaks_to_fix: int = 10
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/agent.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例
settings = Settings()
