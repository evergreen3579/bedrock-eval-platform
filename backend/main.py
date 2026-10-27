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

# 확정된 3개 모델 라우팅 설정
MODEL_ROUTING = {
    "Gemini-2.5-Flash": {
        "provider": "gemini",
        "candidates": ["gemini-2.5-flash", "gemini-2.0-flash"],
    },
    "Groq-Llama-3.1-8B": {
        "provider": "groq",
        "candidates": ["llama-3.1-8b-instant", "llama3-8b-8192"],
    },
    "Groq-Llama-3.3-70B": {
        "provider": "groq",
        "candidates": ["llama-3.3-70b-versatile", "llama3-70b-8192"],
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
async def evaluate_models(request: Request, request_data: schemas.MultiLLMEvalRequest, db: Session = Depends(get_db)):
    if len(request_data.prompt) > 1000:
        raise HTTPException(status_code=400, detail="프롬프트 길이는 최대 1000자를 초과할 수 없습니다.")

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()

    async def call_gemini(client: httpx.AsyncClient, model_id: str, prompt: str):
        if not gemini_key:
            raise ValueError("서버 .env에 GEMINI_API_KEY가 설정되지 않았습니다.")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": gemini_key}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 700,
                # 내부 추론(Thinking)으로 인한 시간 지연을 방지하기 위해 budget 0 설정
                **({"thinkingConfig": {"thinkingBudget": 0}} if "2.5" in model_id else {})
            }
        }
        res = await client.post(url, headers=headers, json=payload, timeout=25.0)
        if res.status_code != 200:
            raise RuntimeError(f"{model_id} (HTTP {res.status_code})")
        
        data = res.json()
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        cand_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = (prompt_tokens + cand_tokens) or usage.get("totalTokenCount") or len(text_out)
        return text_out, total_tokens

    async def call_groq(client: httpx.AsyncClient, model_id: str, prompt: str):
        if not groq_key:
            raise ValueError("서버 .env에 GROQ_API_KEY가 설정되지 않았습니다.")
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
            raise RuntimeError(f"{model_id} (HTTP {res.status_code})")
        
        data = res.json()
        text_out = data["choices"][0]["message"]["content"]
        total_tokens = data.get("usage", {}).get("total_tokens", len(text_out))
        return text_out, total_tokens

    async with httpx.AsyncClient() as client:
        async def process_single_model(model_name: str, prompt: str):
            route = MODEL_ROUTING.get(model_name, {
                "provider": "gemini",
                "candidates": ["gemini-2.5-flash"]
            })
            provider = route["provider"]
            start_time = time.perf_counter()
            ai_response = None
            real_tokens = 0
            errors = []

            for target_id in route["candidates"]:
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