from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Float, Text
from datetime import datetime

from app.config.database import Base

class AIModelConfig(Base):
    """Configuration for different AI models used in the system"""
    __tablename__ = "ai_model_configs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Model identification
    model_name = Column(String(255), unique=True, nullable=False, index=True)
    model_provider = Column(String(100), nullable=False)  # aws_bedrock, openai, huggingface
    model_id = Column(String(255), nullable=False)  # e.g., "anthropic.claude-v2"
    
    # Model details
    model_type = Column(String(100))  # text_generation, translation, summarization
    supported_languages = Column(JSON)  # List of supported languages
    
    # Configuration parameters
    default_temperature = Column(Float, default=0.7)
    default_max_tokens = Column(Integer, default=2000)
    default_top_p = Column(Float, default=0.9)
    default_top_k = Column(Integer, default=50)
    
    # Advanced parameters
    custom_parameters = Column(JSON)  # Additional model-specific parameters
    
    # Cost tracking
    cost_per_1k_input_tokens = Column(Float)
    cost_per_1k_output_tokens = Column(Float)
    
    # Performance metrics
    avg_latency_ms = Column(Integer)
    success_rate = Column(Float)
    
    # Rate limiting
    requests_per_minute = Column(Integer, default=60)
    tokens_per_minute = Column(Integer, default=100000)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # AWS specific
    aws_region = Column(String(50))
    bedrock_model_arn = Column(String(500))
    
    # Model description
    description = Column(Text)
    use_cases = Column(JSON)  # List of recommended use cases
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime)
    
    def __repr__(self):
        return f"<AIModelConfig {self.model_name} - {self.model_provider}>"


class ModelUsageLog(Base):
    """Track usage of AI models for analytics and cost management"""
    __tablename__ = "model_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Model reference
    model_config_id = Column(Integer, nullable=True, index=True)
    model_name = Column(String(255), nullable=False, index=True)
    
    # User reference
    user_id = Column(Integer, nullable=False, index=True)
    
    # Request details
    request_type = Column(String(100))  # generation, translation, summarization
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_tokens = Column(Integer)
    
    # Performance
    latency_ms = Column(Integer)
    success = Column(Boolean, default=True)
    
    # Cost
    estimated_cost_usd = Column(Float)
    
    # Error tracking
    error_code = Column(String(100))
    error_message = Column(Text)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<ModelUsageLog {self.model_name} - {self.created_at}>"
