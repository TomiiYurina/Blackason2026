from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import requests

router = APIRouter(prefix="/api/tax", tags=["TaxCalculation"])

def get_today_grass_count(username: str) -> int:
    """
    🌿 GitHubパブリックAPIから、本日のコミット数を取得する関数。
    🔒 大文字・小文字まで完璧に一致しているか厳密にチェックします。
    """
    # 💡 GitHubは小文字で叩いてもデータを返してくれますが、返ってきたデータの中に「正式なID」が入っています
    url = f"https://api.github.com/users/{username}/events/public"
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    try:
        response = requests.get(url, timeout=5)
        
        # 🚨 スペルが全然違う場合は、ここで404エラー（存在しない）になる
        if response.status_code == 404:
            return -1  
            
        if response.status_code != 200:
            return 0
            
        events = response.json()
        
        # 🔒【今回の最重要キモ！】大文字・小文字の完全一致チェック
        # GitHubのイベントデータがある場合、その中の最初のイベントから「正式なユーザーID（login）」を抜き出します
        if len(events) > 0:
            # GitHubが認識している正式な大文字小文字のID（例: TomiiYurina）
            official_name = events[0].get("actor", {}).get("login", "")
            
            # 富井さんが画面から入力したID（username）と、大文字小文字も含めて完全に一致するか比較
            if username != official_name:
                # 1文字でも大文字小文字が違ったら、ユーザーが見つからない扱い（-1）にして弾く！
                return -1
        
        commit_count = 0
        for event in events:
            if event.get("type") == "PushEvent":
                created_at = event.get("created_at", "")
                if today_str in created_at or yesterday_str in created_at:
                    payload = event.get("payload", {})
                    commits = payload.get("commits", [])
                    commit_count += len(commits)
        
        # 最低保証ルート
        if commit_count == 0:
            action_count = len(events)
            return action_count if action_count > 0 else 4
                    
        return commit_count
        
    except Exception:
        return 0

# 🌟 最初の入力画面（git.html）から送られてきた名前を動的に受け取るメインAPI
@router.get("/calculate-auto/{username}")
def calculate_tax_auto(username: str):
    today_grass = get_today_grass_count(username)
    
    # 🚨 ユーザーが見つからない、または大文字小文字が間違っている場合にエラーを出す
    if today_grass == -1:
        raise HTTPException(
            status_code=404, 
            detail=f"GitHubユーザー「{username}」が見つかりませんでした。大文字・小文字（例: TやYが大文字か）やスペルを正確に確認してください！"
        )
        
    breakdown = {}
    now = datetime.now()
    current_weekday = now.weekday()  
    current_hour = now.hour
    
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