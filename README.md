backend\venv\Scripts\activate
npm run dev
npm run build
uvicorn main:app --reload
pip freeze > requirements.txt
pip install -r requirements.txt

cd C:\tools\evergreen\aws
ssh -i "bedrock-key.pem" ubuntu@54.227.82.12


npm run build


git add .
git commit -m "feat: 과거 평가 기록 조회 UI 및 로직 추가"
git push

nohup uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &