from database import SessionLocal
from models import LLMEvalResult
from schemas import LLMEvalCreate, LLMEvalResponse

def run_test():
    print("1. Pydantic 스키마 유효성 검사 시작...")
    try:
        # Pydantic을 이용한 입력 데이터 구조 검증
        test_data = LLMEvalCreate(
            model_name="테스트_모델_01",
            prompt="이것은 오타 및 연결 확인을 위한 테스트 프롬프트입니다."
        )
        print("✅ [성공] 스키마 검증을 통과했습니다.")
    except Exception as e:
        print(f"❌ [실패] 스키마 검증 오류 (schemas.py 확인 필요):\n{e}")
        return

    print("\n2. 데이터베이스(RDS) 연결 및 데이터 삽입 시작...")
    db = SessionLocal()
    try:
        # SQLAlchemy 모델로 변환 후 DB에 저장
        new_record = LLMEvalResult(**test_data.model_dump())
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        print(f"✅ [성공] DB에 테스트 데이터가 저장되었습니다. (생성된 레코드 ID: {new_record.id})")

        # 저장된 DB 객체를 다시 Pydantic 응답 스키마로 변환
        response_data = LLMEvalResponse.model_validate(new_record)
        print(f"✅ [성공] 최종 응답 데이터 변환 완료:\n{response_data.model_dump()}")

    except Exception as e:
        print(f"❌ [실패] DB 연결 또는 쿼리 오류 (models.py 확인 필요):\n{e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_test()