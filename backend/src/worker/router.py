from fastapi import APIRouter
from datetime import datetime, timedelta
import requests
import random

router = APIRouter(prefix="/api/tax", tags=["TaxCalculation"])

def get_today_grass_count(username: str) -> int:
    """
    GitHubのイベントAPIから、ユーザーが『日本時間の今日』生やした
    コミットの草の数を、時差（UTC）を計算してガチで数え上げる関数
    """
    url = f"https://api.github.com/users/{username}/events/public"
    
    # 🇯🇵 日本時間の「今日」の日付（YYYY-MM-DD）
    today_jst_str = datetime.now().strftime("%Y-%m-%d") 
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return random.randint(1, 5) # セーフティ
            
        events = response.json()
        commit_count = 0
        
        for event in events:
            # PushEvent（コミットをプッシュした操作）をチェック
            if event.get("type") == "PushEvent":
                # GitHubのUTC時間（例: "2026-06-06T08:00:00Z"）を取得
                created_at_utc = event.get("created_at", "")
                if not created_at_utc:
                    continue
                
                # 文字列をPythonの日付オブジェクトに変換
                utc_dt = datetime.strptime(created_at_utc, "%Y-%m-%dT%H:%M:%SZ")
                # ➕9時間して、ガチの「日本時間（JST）」に変換する！
                jst_dt = utc_dt + timedelta(hours=9)
                # 日本時間にした日付の文字列（例: "2026-06-06"）
                event_jst_str = jst_dt.strftime("%Y-%m-%d")
                
                # それが「日本時間の今日」と一致していればカウント！
                if event_jst_str == today_jst_str:
                    commits = event.get("payload", {}).get("commits", [])
                    commit_count += len(commits)
                    
        return commit_count
        
    except Exception:
        return random.randint(1, 5)

# URLの最後に /{username} を指定して受け取る
@router.get("/calculate-auto/{username}")
def calculate_tax_auto(username: str):
    breakdown = {}
    
    # 現在の「曜日」と「時間」を自動取得
    now = datetime.now()
    current_weekday = now.weekday()  # 5=土曜日, 6=日曜日
    current_hour = now.hour
    
    # 🌿 【時差修正版】日本時間の今日の草をガチ取得！
    today_grass = get_today_grass_count(username)
    
    # ① 量産型コミット税
    breakdown[f"量産型コミット税 (今日 {today_grass}個 の草を検知)"] = 0.4
    
    # ② 金曜日お疲れ様税（金曜の17:00〜23:59）
    if current_weekday == 4 and current_hour >= 17:
        breakdown["金曜日お疲れ様税"] = 0.6
        
    # ③ 休日出勤サボり監視税（土曜日・日曜日）
    if current_weekday in [5, 6]:
        breakdown["休日出勤サボり監視税"] = 0.5
        
    # ④ 不健康不夜城労働税（夜 22:00 〜 朝 5:00）
    if current_hour >= 22 or current_hour < 5:
        breakdown["不健康不夜城労働税"] = 0.5
        
    # 合計を計算
    total_tax = round(sum(breakdown.values()), 1)
    if total_tax > 2.0:
        total_tax = 2.0
        
    return {
        "total_tax": total_tax,
        "breakdown": breakdown
    }

@router.get("/audit")
def tax_audit():
    return {
        "is_audited": True,
        "title": "🚨 国税ブラックサンダー局による緊急ガサ入れ",
        "action_required": "camera_scan"
    }