from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typing import List
import asyncio
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

app = FastAPI(title="Multi-LLM Evaluation Platform (Google Gemini & Groq)")

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

# API 서버에서 조회한 실제 사용 가능 모델 캐시
CACHED_GEMINI_MODELS: List[str] = []
CACHED_GROQ_MODELS: List[str] = []

async def get_gemini_models(client: httpx.AsyncClient, api_key: str) -> List[str]:
    global CACHED_GEMINI_MODELS
    if CACHED_GEMINI_MODELS:
        return CACHED_GEMINI_MODELS

    url = "https://generativelanguage.googleapis.com/v1beta/models"
    try:
        res = await client.get(url, headers={"x-goog-api-key": api_key}, timeout=10.0)
        if res.status_code != 200:
            res = await client.get(f"{url}?key={api_key}", timeout=10.0)
        
        if res.status_code == 200:
            data = res.json()
            valid = []
            for m in data.get("models", []):
                methods = m.get("supportedGenerationMethods", [])
                name = m.get("name", "").replace("models/", "")
                # 무료 티어에서 100% 작동하는 flash 계열 텍스트 모델만 수집
                if (
                    "generateContent" in methods
                    and "gemini" in name
                    and "flash" in name
                    and not any(x in name for x in ["vision", "embedding", "tts", "image", "audio", "thinking"])
                ):
                    valid.append(name)
            if valid:
                CACHED_GEMINI_MODELS = valid
                return valid
    except Exception:
        pass
    return ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"]

async def get_groq_models(client: httpx.AsyncClient, api_key: str) -> List[str]:
    global CACHED_GROQ_MODELS
    if CACHED_GROQ_MODELS:
        return CACHED_GROQ_MODELS

    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        res = await client.get(url, headers=headers, timeout=10.0)
        if res.status_code == 200:
            data = res.json()
            valid = []
            for m in data.get("data", []):
                mid = m.get("id", "")
                # 음성(whisper), 보안가드(guard), 비전(vision), 추론전용(deepseek) 등을 제외한 순수 채팅 LLM 필터링
                if not any(x in mid.lower() for x in ["whisper", "guard", "vision", "tts", "playai", "embed", "allam"]):
                    valid.append(mid)
            if valid:
                CACHED_GROQ_MODELS = valid
                return valid
    except Exception:
        pass
    return ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

def pick_candidates(available: List[str], prefer_keywords: List[str]) -> List[str]:
    picked = []
    for kw in prefer_keywords:
        for m in available:
            if kw in m.lower() and m not in picked:
                picked.append(m)
    for m in available:
        if m not in picked:
            picked.append(m)
    return picked[:5]

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
async def evaluate_models(request: Request, request_data: schemas.MultiLLMEvalRequest, db: Session = Depends(get_db)):
    if len(request_data.prompt) > 1000:
        raise HTTPException(status_code=400, detail="프롬프트 길이는 최대 1000자를 초과할 수 없습니다.")

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()

    async def call_gemini(client: httpx.AsyncClient, model_id: str, prompt: str):
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY 미설정")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": gemini_key}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 700,
            }
        }
        res = await client.post(url, headers=headers, json=payload, timeout=25.0)
        if res.status_code != 200:
            # URL 쿼리 파라미터 인증 폴백
            res = await client.post(f"{url}?key={gemini_key}", json=payload, timeout=25.0)
        if res.status_code != 200:
            raise RuntimeError(f"{model_id}({res.status_code})")
        
        data = res.json()
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        cand_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = (prompt_tokens + cand_tokens) or usage.get("totalTokenCount") or len(text_out)
        return text_out, total_tokens

    async def call_groq(client: httpx.AsyncClient, model_id: str, prompt: str):
        if not groq_key:
            raise ValueError("GROQ_API_KEY 미설정")
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {groq_key}"
        }
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": "질문에 대해 한국어로 명확하고 자연스럽게 답변하세요."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 700,
        }
        res = await client.post(url, headers=headers, json=payload, timeout=25.0)
        if res.status_code != 200:
            raise RuntimeError(f"{model_id}({res.status_code})")
        
        data = res.json()
        text_out = data["choices"][0]["message"]["content"]
        total_tokens = data.get("usage", {}).get("total_tokens", len(text_out))
        return text_out, total_tokens

    async with httpx.AsyncClient() as client:
        # Google 및 Groq 서버에서 현재 활성화된 실제 모델 목록을 병렬 조회
        gemini_avail, groq_avail = await asyncio.gather(
            get_gemini_models(client, gemini_key),
            get_groq_models(client, groq_key)
        )

        # 각 선택 항목에 맞는 최적의 실제 모델 후보군 자동 배정
        routing_map = {
            "Gemini-2.5-Flash": (
                "gemini",
                pick_candidates(gemini_avail, ["2.5-flash", "flash-latest", "2.0-flash", "flash"])
            ),
            "Groq-Llama-3.1-8B": (
                "groq",
                pick_candidates(groq_avail, ["8b", "instant", "small", "gemma", "qwen", "llama"])
            ),
            "Groq-Llama-3.3-70B": (
                "groq",
                pick_candidates(groq_avail, ["70b", "versatile", "maverick", "scout", "llama-4", "llama-3.3", "llama"])
            ),
        }

        async def process_single_model(model_name: str, prompt: str):
            provider, candidates = routing_map.get(
                model_name, ("gemini", gemini_avail[:3])
            )
            start_time = time.perf_counter()
            ai_response = None
            real_tokens = 0
            errors = []

            for target_id in candidates:
                try:
                    if provider == "groq":
                        ai_response, real_tokens = await call_groq(client, target_id, prompt)
                    else:
                        ai_response, real_tokens = await call_gemini(client, target_id, prompt)
                    break
                except Exception as e:
                    errors.append(str(e))

            if not ai_response:
                ai_response = f"[{model_name}] 호출 실패: {', '.join(errors)}"
                real_tokens = 0

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            return models.LLMEvalResult(
                model_name=model_name,
                prompt=prompt,
                response=ai_response,
                evaluation_score=0,
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