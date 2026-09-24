from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from database import Base

class LLMEvalResult(Base):
    __tablename__ = "llm_eval_results"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(50), nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    evaluation_score = Column(Integer, nullable=True)
    
    # [신규 추가] 성능 지표 비교를 위한 컬럼
    processing_time_ms = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())