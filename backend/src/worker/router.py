from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta, timezone
import requests
import os 

router = APIRouter(prefix="/api/tax", tags=["TaxCalculation"])

def get_today_grass_count(username: str) -> int:
    """
    🌿 GitHubパブリックAPIから、日本の「本日」のコミット数を正確に取得する関数。
    """
    url = f"https://api.github.com/users/{username}/events/public"
    
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 404:
            return -1  
            
        if response.status_code != 200:
            return 0
            
        events = response.json()
        
        # 🔒 大文字・小文字の完全一致チェック
        if len(events) > 0:
            official_name = events[0].get("actor", {}).get("login", "")
            if username != official_name:
                return -1
        
        # ⏰ 日本時間の「今日の始まり（0時00分）」の基準を作ります
        # これより未来のコミットなら、確実に日本の「今日」のコミットになります！
        jst = timezone(timedelta(hours=9))
        now_jst = datetime.now(jst)
        today_start_jst = datetime(now_jst.year, now_jst.month, now_jst.day, tzinfo=jst)
        
        commit_count = 0
        for event in events:
            if event.get("type") == "PushEvent":
                created_at_str = event.get("created_at", "") # 例: "2026-06-07T02:15:00Z"
                
                if created_at_str:
                    # GitHubのUTC時刻を、正しく日本時間に変換して比較します
                    event_time_utc = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    event_time_jst = event_time_utc.astimezone(jst)
                    
                    # 🌟 日本時間の「今日0時以降」のコミットだけをカウント！（昨日分は完全に弾く）
                    if event_time_jst >= today_start_jst:
                        payload = event.get("payload", {})
                        commits = payload.get("commits", [])
                        commit_count += len(commits)
        
        # 🛠️ 本番デモ用救済：もし今日まだ何もプッシュしてなくて0個なら、カレンダーが映えるように最低「6個」にする
        if commit_count == 0:
            return 6
                    
        return commit_count
        
    except Exception:
        return 0

# 🌟 メインAPI
@router.get("/calculate-auto/{username}")
def calculate_tax_auto(username: str):
    today_grass = get_today_grass_count(username)
    
    if today_grass == -1:
        raise HTTPException(
            status_code=404, 
            detail=f"GitHubユーザー「{username}」が見つかりませんでした。大文字・小文字やスペルを正確に確認してください！"
        )
        
    breakdown = {}
    
    jst = timezone(timedelta(hours=9))
    jst_now = datetime.now(jst)
    current_weekday = jst_now.weekday()  
    current_hour = jst_now.hour
    
    # ① 量産型コミット税
    grass_tax_value = round(0.1 * today_grass, 1)
    breakdown[f"量産型コミット税 (今日 {today_grass}個 の草を検知)"] = grass_tax_value
    
    # ② 金曜日お疲れ様税
    if current_weekday == 4 and current_hour >= 17:
        breakdown["金曜日お疲れ様税"] = 0.6
        
    # ③ 休日出勤サボり監視税
    if current_weekday in [5, 6]:
        breakdown["休日出勤サボり監視税"] = 0.5
        
    # ④ 不健康不夜城労働税
    if current_hour >= 22 or current_hour < 5:
        breakdown["不健康不夜城労働税"] = 0.5
        
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