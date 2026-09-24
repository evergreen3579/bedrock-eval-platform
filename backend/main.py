from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typing import List
import asyncio
import random

import models
import schemas
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Amazon Bedrock 기반 다중 대형언어모델 평가 플랫폼")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# [신규 추가] 다중 모델 병렬 처리 라우터
@app.post("/mock-bedrock-eval/", response_model=List[schemas.LLMEvalResponse])
async def mock_bedrock_evaluation(request_data: schemas.MultiLLMEvalRequest, db: Session = Depends(get_db)):
    """
    여러 모델의 평가 요청을 동시에 처리하고 가짜 데이터를 반환합니다.
    """
    async def process_single_model(model_name: str, prompt: str):
        # API 호출 지연 시간 시뮬레이션 (1초 ~ 3초)
        delay = random.uniform(1.0, 3.0)
        await asyncio.sleep(delay)
        
        # 가짜 성능 지표 및 응답 생성
        mock_response = f"[{model_name}] 모델의 응답입니다. '{prompt}' 처리 완료."
        mock_score = random.randint(75, 98)
        mock_time_ms = int(delay * 1000)
        mock_tokens = random.randint(150, 500)
        
        return models.LLMEvalResult(
            model_name=model_name,
            prompt=prompt,
            response=mock_response,
            evaluation_score=mock_score,
            processing_time_ms=mock_time_ms,
            token_count=mock_tokens
        )

    # 선택된 여러 모델을 비동기로 동시 실행
    tasks = [process_single_model(model, request_data.prompt) for model in request_data.models]
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