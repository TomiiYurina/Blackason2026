from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.src.worker.router import router as tax_router

app = FastAPI(title="ブラックサンダー庁 API")

# Reactからのアクセスを許可する必須設定（CORS）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🌟 あなたの作った計算・税務調査APIをアプリに登録！
app.include_router(tax_router)

@app.get("/")
def index():
    return {"status": "ブラックサンダー庁国税局、正常稼働中"}