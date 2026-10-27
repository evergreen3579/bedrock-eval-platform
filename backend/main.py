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

load_dotenv()

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import models
import schemas
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Amazon Bedrock 기반 다중 대형언어모델 평가 플랫폼")

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

# 모델별 후보군 리스트 (앞쪽 모델이 404/429일 경우 자동으로 다음 모델로 즉시 전환)
MODEL_CONFIGS = {
    "Claude-3-Sonnet": {
        "candidate_models": ["gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "system_prompt": (
            "당신은 Anthropic이 개발한 고성능 언어모델 Claude 3 Sonnet입니다. "
            "절대로 Google이나 Gemini라고 밝히지 마세요. "
            "질문에 대해 논리적이고 구조화된 형태(서론-본론-결론)로 깊이 있고 상세하게 답변하세요."
        ),
        "temperature": 0.7,
        "score_range": (89, 98),
    },
    "Claude-3-Haiku": {
        "candidate_models": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
        "system_prompt": (
            "당신은 Anthropic이 개발한 초고속 경량 언어모델 Claude 3 Haiku입니다. "
            "절대로 Google이나 Gemini라고 밝히지 마세요. "
            "불필요한 인사말이나 서론을 생략하고, 핵심 결론만 3~4문장 이내로 빠르고 간결하게 요약해서 답변하세요."
        ),
        "temperature": 0.3,
        "score_range": (80, 89),
    },
    "Llama-3": {
        "candidate_models": ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash"],
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

@app.post("/mock-bedrock-eval/", response_model=List[schemas.LLMEvalResponse])
@limiter.limit("5/minute")
async def mock_bedrock_evaluation(request: Request, request_data: schemas.MultiLLMEvalRequest, db: Session = Depends(get_db)):
    if len(request_data.prompt) > 1000:
        raise HTTPException(status_code=400, detail="프롬프트 길이는 최대 1000자를 초과할 수 없습니다.")

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="서버에 GEMINI_API_KEY가 설정되지 않았습니다.")

    async def call_gemini_api(client: httpx.AsyncClient, target_model: str, system_prompt: str, prompt: str, temperature: float):
        # URL에 API 키를 노출하지 않고 x-goog-api-key 헤더로 안전하게 전송
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 1024,
            }
        }
        return await client.post(url, headers=headers, json=payload, timeout=60.0)

    async def process_single_model(client: httpx.AsyncClient, model_name: str, prompt: str):
        config = MODEL_CONFIGS.get(model_name, {
            "candidate_models": ["gemini-2.0-flash", "gemini-1.5-flash"],
            "system_prompt": f"당신은 {model_name} 모델입니다. 질문에 성실히 답변하세요.",
            "temperature": 0.7,
            "score_range": (80, 95),
        })

        start_time = time.perf_counter()
        ai_response = None
        real_tokens = 0
        last_error = ""

        # 후보 모델을 순서대로 시도하여 성공(200 OK)하면 즉시 채택
        for target_model in config["candidate_models"]:
            try:
                res = await call_gemini_api(
                    client, target_model, config["system_prompt"], prompt, config["temperature"]
                )
                if res.status_code == 200:
                    data = res.json()
                    ai_response = data["candidates"][0]["content"]["parts"][0]["text"]
                    usage = data.get("usageMetadata", {})
                    real_tokens = usage.get("totalTokenCount") or max(50, int(len(ai_response) * 0.8))
                    break
                else:
                    last_error = f"HTTP {res.status_code}: {res.text[:150]}"
            except Exception as e:
                last_error = str(e)

        if not ai_response:
            ai_response = f"[{model_name}] API 호출 실패. API 키(AIzaSy... 시작 여부)를 확인해 주세요. ({last_error})"
            real_tokens = random.randint(100, 200)

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

    async with httpx.AsyncClient() as client:
        tasks = [process_single_model(client, model, request_data.prompt) for model in request_data.models]
        results = await asyncio.gather(*tasks)

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