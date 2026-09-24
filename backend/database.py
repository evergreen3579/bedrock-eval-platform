import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# 현재 파일(database.py)이 위치한 backend 폴더 내부의 .env 절대 경로를 찾아 로드
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(env_path)

# 환경 변수 할당
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# .env 로드 실패 방지용 안전장치(에러 메시지)
if not DB_PORT:
    raise ValueError(f"🚨 환경 변수를 불러오지 못했습니다. 경로({env_path})에 .env 파일이 정확한 이름으로 존재하는지 확인하세요.")

# PostgreSQL 연결 URL 조합
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# DB 엔진 및 세션 생성
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 모델 매핑을 위한 Base 객체 선언 (models.py에서 참조함)
Base = declarative_base()