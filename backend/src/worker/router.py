from fastapi import APIRouter
from pydantic import BaseModel
import random

# フロントエンドや演出担当が呼び出しやすいようにURLの頭に /api/tax を付ける
router = APIRouter(prefix="/api/tax", tags=["TaxCalculation"])

# 1. フロントから送られてくるデータの形を定義（Pydanticモデル）
class TaxRequest(BaseModel):
    # 基本実績
    ai_consults: int        # AI相談回数
    commits: int           # コミット数
    bugs: int              # バグ発生数
    hours_left: float       # 締切までの時間（時間単位）

    # ネタ税フラグ（チェックボックスなどでTrue/Falseで受け取る想定）
    chatgpt_dependence: bool = False
    merge_conflict: bool = False
    unknown_error: bool = False
    all_nighter: bool = False

# 2. 税金計算API (POST /api/tax/calculate)
@router.post("/calculate")
def calculate_tax(data: TaxRequest):
    breakdown = {}
    
    # --- 【基本税】の計算 ---
    # AI利用税: 1回につき 0.03本
    breakdown["AI利用税"] = round(data.ai_consults * 0.03, 2)
    
    # コミット税: 1回につき 0.05本
    breakdown["コミット税"] = round(data.commits * 0.05, 2)
    
    # バグ復旧税: 1件につき 0.1本
    breakdown["バグ復旧税"] = round(data.bugs * 0.1, 2)
    
    # --- 【締切補正（重税化）】 ---
    # 締切が3時間未満なら、ここまでの基本税の合計が1.5倍になる「直前滑り込み重加算税」
    base_total = sum(breakdown.values())
    if data.hours_left <= 3.0:
        breakdown["直前滑り込み重加算税"] = round(base_total * 0.5, 2)

    # --- 【ネタ税】の実装（エンジニアあるある） ---
    if data.chatgpt_dependence:
        breakdown["ChatGPT依存税"] = 0.5
    if data.merge_conflict:
        breakdown["Merge Conflict税"] = 1.2
    if data.unknown_error:
        breakdown["原因不明エラー税"] = 0.8
    if data.all_nighter:
        breakdown["徹夜開発税"] = 2.0

    # すべての税の合計本数を計算
    total_tax = round(sum(breakdown.values()), 2)

    return {
        "total_tax": total_tax,
        # 画面に表示しやすいように、0本以上の税金だけを絞り込んでフロントに返す
        "breakdown": {k: v for k, v in breakdown.items() if v > 0}
    }

# 3. 税務調査API (GET /api/tax/audit)
@router.get("/audit")
def tax_audit():
    # 理不尽な追徴課税イベントのリスト
    audit_events = [
        {
            "reason": "【密告】本番環境クラッシュを申告していない疑いがあります。",
            "additional_tax": 3.5,
            "comment": "本番環境での強制プッシュ（git push -f）が確認されました。即時徴収します。"
        },
        {
            "reason": "【無申告】金曜17時以降のコード変更が検知されました。",
            "additional_tax": 1.5,
            "comment": "週末の平穏を脅かす「金曜17時バグ税」の脱税は重罪です。"
        },
        {
            "reason": "【インデント汚職】半角スペースとタブが混在しています。",
            "additional_tax": 0.8,
            "comment": "コードの美観を著しく損ねた罪による追徴課税です。"
        },
        {
            "reason": "【国税局の慈悲】いつも開発お疲れ様です！",
            "additional_tax": -1.0,  # 免除イベント！
            "comment": "頑張るエンジニアにブラックサンダーを1本支給します。（納税額から差し引き）"
        }
    ]
    
    # 35%の確率でランダムに税務調査（嫌がらせ）が発生、65%は「異常なし」
    is_audited = random.random() < 0.35
    
    if is_audited:
        event = random.choice(audit_events)
        return {
            "is_audited": True,
            "title": "🚨 国税ブラックサンダー局による緊急税務調査",
            "reason": event["reason"],
            "additional_tax": event["additional_tax"],
            "comment": event["comment"]
        }
    else:
        return {
            "is_audited": False,
            "title": "清廉潔白",
            "reason": "現在のところ、不審なコミットや隠蔽されたバグは見つかりませんでした。",
            "additional_tax": 0.0,
            "comment": "引き続き適正なブラックサンダー消費を心がけてください。"
        }