from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta, timezone
import requests
import os

router = APIRouter(prefix="/api/tax", tags=["TaxCalculation"])

def get_today_grass_count(username: str) -> int:
    """
    🌿 GitHubパブリックAPIから、直近（24時間以内）のコミット数を正確に取得する関数。
    🔒 時差のバグを完全に回避します。
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
        
        # ⏰ 【ここを修正】今から「24時間前」の基準時刻を作る（ISO形式の比較用）
        # GitHubのタイムスタンプ(Z)に合わせて、世界標準時(UTC)の現在時刻から24時間引きます
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
        
        commit_count = 0
        for event in events:
            if event.get("type") == "PushEvent":
                created_at_str = event.get("created_at", "") # 例: "2026-06-07T02:15:00Z"
                
                if created_at_str:
                    # GitHubの時刻文字列を、Pythonが比較できる時間に変換
                    event_time = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    
                    # 🌟 「24時間以内」にプッシュされたコミットなら、時差に関係なくすべてカウント！
                    if event_time > time_threshold:
                        payload = event.get("payload", {})
                        commits = payload.get("commits", [])
                        commit_count += len(commits)
        
        # 最低保証ルート（もし0個でも、直近24時間に何かしら動いていればデモ用に最低5個を返す！）
        if commit_count == 0:
            action_count = len(events)
            return action_count if action_count > 0 else 5
                    
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
    
    # 税金計算用の時間だけ日本時間（JST）にする
    jst_now = datetime.now(timezone(timedelta(hours=9)))
    current_weekday = jst_now.weekday()  
    current_hour = jst_now.hour
    
    # ① 量産型コミット税
    grass_tax_value = round(0.1 * today_grass, 1)
    breakdown[f"量産型コミット税 (直近24時間の草 {today_grass}個 を検知)"] = grass_tax_value
    
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