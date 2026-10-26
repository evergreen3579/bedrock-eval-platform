from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typing import List
import asyncio
import random
import os
import time
import httpx
from dotenv import load_dotenv

# .env 파일에서 환경 변수(GEMINI_API_KEY 등) 로드
load_dotenv()

# [Phase 1 추가] Rate Limit 라이브러리 임포트
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import models
import schemas
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

# [Phase 1 추가] Nginx 프록시 환경을 고려하여 사용자의 실제 IP를 추출하도록 Limiter 설정
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Amazon Bedrock 기반 다중 대형언어모델 평가 플랫폼")

# [Phase 1 추가] 앱에 Limiter 인스턴스 주입 및 429 에러 핸들러 등록
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://bedrock-eval-frontend-2026.s3-website-us-east-1.amazonaws.com",
        "https://dwxuo920pm056.cloudfront.net"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모델별 Gemini 체급 및 페르소나 매핑 설정
MODEL_CONFIGS = {
    "Claude-3-Sonnet": {
        "gemini_model": "gemini-2.5-pro",
        "fallback_model": "gemini-2.5-flash",
        "system_prompt": (
            "당신은 Anthropic이 개발한 고성능 언어모델 Claude 3 Sonnet입니다. "
            "절대로 Google이나 Gemini라고 밝히지 마세요. "
            "질문에 대해 논리적이고 구조화된 형태(서론-본론-결론)로 깊이 있고 상세하게 답변하세요."
        ),
        "temperature": 0.7,
        "score_range": (89, 98),
    },
    "Claude-3-Haiku": {
        "gemini_model": "gemini-2.5-flash",
        "fallback_model": "gemini-2.5-flash",
        "system_prompt": (
            "당신은 Anthropic이 개발한 초고속 경량 언어모델 Claude 3 Haiku입니다. "
            "절대로 Google이나 Gemini라고 밝히지 마세요. "
            "불필요한 인사말이나 서론을 생략하고, 핵심 결론만 3~4문장 이내로 빠르고 간결하게 요약해서 답변하세요."
        ),
        "temperature": 0.3,
        "score_range": (80, 89),
    },
    "Llama-3": {
        "gemini_model": "gemini-2.5-flash-lite",
        "fallback_model": "gemini-2.5-flash",
        "system_prompt": (
            "당신은 Meta가 개발한 오픈소스 대형언어모델 Llama 3입니다. "
            "절대로 Google이나 Gemini라고 밝히지 마세요. "
            "친근하고 직관적인 톤앤매너를 유지하며, 핵심 내용을 개조식 글머리 기호(•)로 정리하여 가독성 높게 답변하세요."
        ),
        "temperature": 0.9,
        "score_range": (84, 93),
    },
}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "백엔드 서버가 정상적으로 구동 중입니다."}

@app.get("/test-db")
def test_db_connection(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1")).scalar()
        return {
            "status": "success", 
            "message": "RDS PostgreSQL 데이터베이스 연결 성공!", 
            "result_value": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB 연결 실패: {str(e)}")

# [Phase 1 추가] 라우터에 분당 5회 트래픽 제한 적용 (Request 객체 필수)
@app.post("/mock-bedrock-eval/", response_model=List[schemas.LLMEvalResponse])
@limiter.limit("5/minute")
async def mock_bedrock_evaluation(request: Request, request_data: schemas.MultiLLMEvalRequest, db: Session = Depends(get_db)):
    """
    여러 모델의 평가 요청을 비동기로 동시에 처리하고 결과를 반환합니다.
    """
    # [Phase 1 추가] 서버 보호를 위한 백엔드 입력 글자 수 강제 검증 로직
    if len(request_data.prompt) > 1000:
        raise HTTPException(status_code=400, detail="프롬프트 길이는 최대 1000자를 초과할 수 없습니다.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="서버에 GEMINI_API_KEY가 설정되지 않았습니다.")

    async def call_gemini_api(client: httpx.AsyncClient, target_model: str, system_prompt: str, prompt: str, temperature: float):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 1024,
            }
        }
        return await client.post(url, json=payload, timeout=60.0)

    async def process_single_model(client: httpx.AsyncClient, model_name: str, prompt: str):
        config = MODEL_CONFIGS.get(model_name, {
            "gemini_model": "gemini-2.5-flash",
            "fallback_model": "gemini-2.5-flash",
            "system_prompt": f"당신은 {model_name} 모델입니다. 질문에 성실히 답변하세요.",
            "temperature": 0.7,
            "score_range": (80, 95),
        })

        start_time = time.perf_counter()
        
        try:
            # 1차 호출 (지정된 체급 모델)
            res = await call_gemini_api(
                client, config["gemini_model"], config["system_prompt"], prompt, config["temperature"]
            )
            
            # 무료 할당량 초과(429) 또는 모델 호환 오류 시 즉시 폴백 모델(flash)로 재시도
            if res.status_code != 200 and config["gemini_model"] != config["fallback_model"]:
                res = await call_gemini_api(
                    client, config["fallback_model"], config["system_prompt"], prompt, config["temperature"]
                )

            res.raise_for_status()
            data = res.json()

            # 실제 응답 텍스트 추출
            ai_response = data["candidates"][0]["content"]["parts"][0]["text"]
            
            # 실제 토큰 사용량 추출 (메타데이터가 없을 경우 글자 수 기반 추정)
            usage = data.get("usageMetadata", {})
            real_tokens = usage.get("totalTokenCount") or max(50, int(len(ai_response) * 0.8))

        except Exception as e:
            ai_response = f"[{model_name}] 일시적인 API 통신 지연이 발생했습니다. 잠시 후 다시 시도해 주세요. (상세: {str(e)})"
            real_tokens = random.randint(100, 250)

        # 실제 소요 시간(ms) 계산
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        eval_score = random.randint(*config["score_range"])

        return models.LLMEvalResult(
            model_name=model_name,
            prompt=prompt,
            response=ai_response,
            evaluation_score=eval_score,
            processing_time_ms=elapsed_ms,
            token_count=real_tokens
        )

    # 단일 AsyncClient 세션 안에서 선택된 여러 모델을 비동기 병렬 실행
    async with httpx.AsyncClient() as client:
        tasks = [process_single_model(client, model, request_data.prompt) for model in request_data.models]
        results = await asyncio.gather(*tasks)

    # 생성된 모든 결과를 DB에 순차 저장
    saved_records = []
    try:
        for record in results:
            db.add(record)
            db.commit()
            db.refresh(record)
            saved_records.append(record)
        return saved_records
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"데이터 저장 실패: {str(e)}")

@app.get("/evaluations/", response_model=List[schemas.LLMEvalResponse])
def read_evaluations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        records = db.query(models.LLMEvalResult).offset(skip).limit(limit).all()
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 조회 실패: {str(e)}")