from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/tax", tags=["TaxCalculation"])

@router.get("/calculate-auto")
def calculate_tax_auto():
    breakdown = {}
    
    # 現在の「曜日」と「時間」をガチ自動取得
    now = datetime.now()
    current_weekday = now.weekday()  # 0=月, 4=金, 5=土, 6=日
    current_hour = now.hour
    
    # ① 量産型コミット税（全員一律で必ず入るベース税）
    breakdown["量産型コミット税"] = 0.4
    
    # ② 金曜日お疲れ様税（金曜の17:00〜23:59）
    if current_weekday == 4 and current_hour >= 17:
        breakdown["金曜日お疲れ様税"] = 0.6
        
    # ③ 休日出勤サボり監視税（土曜日・日曜日）
    if current_weekday in [5, 6]:
        breakdown["休日出勤サボり監視税"] = 0.5
        
    # ④ 不健康不夜城労働税（夜 22:00 〜 朝 5:00）
    if current_hour >= 22 or current_hour < 5:
        breakdown["不健康不夜城労働税"] = 0.5
        
    # 合計を計算（綺麗に小数点第1位で丸める）
    total_tax = round(sum(breakdown.values()), 1)
    
    return {
        "total_tax": total_tax,
        "breakdown": breakdown
    }

# 納税ボタンの後の「カメラ起動（画像検出）」へ繋ぐためのAPI
@router.get("/audit")
def tax_audit():
    return {
        "is_audited": True,
        "title": "🚨 国税ブラックサンダー局による緊急ガサ入れ",
        "action_required": "camera_scan"
    }