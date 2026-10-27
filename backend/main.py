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

# 모델별 페르소나 및 선호 키워드 설정
MODEL_CONFIGS = {
    "Claude-3-Sonnet": {
        "prefer_keywords": ["2.5-pro", "pro", "2.5-flash", "flash"],
        "system_prompt": (
            "당신은 Anthropic이 개발한 고성능 언어모델 Claude 3 Sonnet입니다. "
            "절대로 Google이나 Gemini라고 밝히지 마세요. "
            "질문에 대해 논리적이고 구조화된 형태(서론-본론-결론)로 깊이 있고 상세하게 답변하세요."
        ),
        "temperature": 0.7,
        "score_range": (89, 98),
    },
    "Claude-3-Haiku": {
        "prefer_keywords": ["2.5-flash", "2.0-flash", "flash"],
        "system_prompt": (
            "당신은 Anthropic이 개발한 초고속 경량 언어모델 Claude 3 Haiku입니다. "
            "절대로 Google이나 Gemini라고 밝히지 마세요. "
            "불필요한 인사말이나 서론을 생략하고, 핵심 결론만 3~4문장 이내로 빠르고 간결하게 요약해서 답변하세요."
        ),
        "temperature": 0.3,
        "score_range": (80, 89),
    },
    "Llama-3": {
        "prefer_keywords": ["flash-lite", "lite", "flash"],
        "system_prompt": (
            "당신은 Meta가 개발한 오픈소스 대형언어모델 Llama 3입니다. "
            "절대로 Google이나 Gemini라고 밝히지 마세요. "
            "친근하고 직관적인 톤앤매너를 유지하며, 핵심 내용을 개조식 글머리 기호(•)로 정리하여 가독성 높게 답변하세요."
        ),
        "temperature": 0.9,
        "score_range": (84, 93),
    },
}

# 사용 가능한 모델 목록 캐시
AVAILABLE_GEMINI_MODELS: List[str] = []

async def get_available_models(client: httpx.AsyncClient, api_key: str) -> List[str]:
    global AVAILABLE_GEMINI_MODELS
    if AVAILABLE_GEMINI_MODELS:
        return AVAILABLE_GEMINI_MODELS

    url = "https://generativelanguage.googleapis.com/v1beta/models"
    headers = {"x-goog-api-key": api_key}
    try:
        res = await client.get(url, headers=headers, timeout=15.0)
        if res.status_code != 200:
            res = await client.get(f"{url}?key={api_key}", timeout=15.0)
        
        if res.status_code == 200:
            data = res.json()
            valid_models = []
            for m in data.get("models", []):
                methods = m.get("supportedGenerationMethods", [])
                name = m.get("name", "").replace("models/", "")
                # 텍스트 생성(generateContent)을 지원하는 순수 gemini 모델만 필터링
                if "generateContent" in methods and "gemini" in name and "vision" not in name and "embedding" not in name and "tts" not in name and "image" not in name:
                    valid_models.append(name)
            if valid_models:
                AVAILABLE_GEMINI_MODELS = valid_models
                return valid_models
    except Exception:
        pass

    return ["gemini-2.5-flash", "gemini-2.0-flash"]

def select_candidates_for_persona(available: List[str], prefer_keywords: List[str]) -> List[str]:
    candidates = []
    for kw in prefer_keywords:
        for m in available:
            if kw in m and m not in candidates:
                candidates.append(m)
    for m in available:
        if m not in candidates:
            candidates.append(m)
    return candidates[:4]

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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
        # 모델 버전별 호환성을 위해 시스템 프롬프트와 사용자 질문을 결합하여 전달
        combined_text = f"[System Instruction]\n{system_prompt}\n\n[User Prompt]\n{prompt}"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": combined_text}]}
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 1024,
            }
        }
        return await client.post(url, headers=headers, json=payload, timeout=60.0)

    async with httpx.AsyncClient() as client:
        # 1. 현재 API 키로 실제 호출 가능한 모델 리스트 자동 획득
        available_models = await get_available_models(client, api_key)

        async def process_single_model(model_name: str, prompt: str):
            config = MODEL_CONFIGS.get(model_name, {
                "prefer_keywords": ["flash"],
                "system_prompt": f"당신은 {model_name} 모델입니다. 질문에 성실히 답변하세요.",
                "temperature": 0.7,
                "score_range": (80, 95),
            })

            candidate_models = select_candidates_for_persona(available_models, config["prefer_keywords"])
            start_time = time.perf_counter()
            ai_response = None
            real_tokens = 0
            error_logs = []

            for target_model in candidate_models:
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
                        error_logs.append(f"{target_model}({res.status_code})")
                except Exception as e:
                    error_logs.append(f"{target_model}({str(e)[:40]})")

            if not ai_response:
                ai_response = f"[{model_name}] 호출 실패. 시도한 모델 내역: {', '.join(error_logs)}"
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

        tasks = [process_single_model(model, request_data.prompt) for model in request_data.models]
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