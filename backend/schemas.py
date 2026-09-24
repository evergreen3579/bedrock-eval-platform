from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

# 1. 공통 속성
class LLMEvalBase(BaseModel):
    model_name: str
    prompt: str
    response: Optional[str] = None
    evaluation_score: Optional[int] = None
    processing_time_ms: Optional[int] = None
    token_count: Optional[int] = None

# 2. 단일 데이터 생성 및 응답 스키마
class LLMEvalCreate(LLMEvalBase):
    pass

class LLMEvalResponse(LLMEvalBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# 3. [신규 추가] 프론트엔드에서 배열 형태로 여러 모델을 보낼 때 사용하는 스키마
class MultiLLMEvalRequest(BaseModel):
    models: List[str]
    prompt: str