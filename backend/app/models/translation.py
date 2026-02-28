from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.config.database import Base

class TranslationMethod(str, enum.Enum):
    AWS_TRANSLATE = "aws_translate"
    INDIC_TRANS = "indic_trans"
    GOOGLE_TRANSLATE = "google_translate"
    CUSTOM_MODEL = "custom_model"

class Translation(Base):
    __tablename__ = "translations"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=True, index=True)
    
    # Translation details
    source_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    
    # Language information
    source_language = Column(String(50), nullable=False, index=True)
    target_language = Column(String(50), nullable=False, index=True)
    
    # Translation metadata
    method = Column(SQLEnum(TranslationMethod), default=TranslationMethod.AWS_TRANSLATE)
    model_version = Column(String(100))
    translation_time_ms = Column(Integer)
    
    # AWS Translate specific
    aws_job_id = Column(String(255))
    aws_terminology_name = Column(String(255))  # Custom terminology for domain-specific terms
    
    # Quality metrics
    confidence_score = Column(Float)  # Translation confidence (0-1)
    quality_score = Column(Float)  # Human or AI-rated quality (0-100)
    
    # Tone preservation
    tone_preserved = Column(String(50))  # Whether tone was maintained
    
    # Character counts
    source_char_count = Column(Integer)
    target_char_count = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    content = relationship("Content", back_populates="translations")
    
    def __repr__(self):
        return f"<Translation {self.id} - {self.source_language} to {self.target_language}>"
