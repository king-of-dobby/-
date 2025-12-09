# payment_backend.py
# Flask backend for payment session creation / approval webhook / code management
# NOTE: This is a template. You MUST replace placeholders with real PG API endpoints & keys.

from flask import Flask, request, jsonify, redirect
import sqlite3
import os
import uuid
import requests
from datetime import datetime

app = Flask(__name__)

# Configure via environment variables
# Example:
# KAKAOPAY_ADMIN_KEY = os.environ.get("KAKAOPAY_ADMIN_KEY")
KAKAOPAY_ADMIN_KEY = os.environ.get("KAKAOPAY_ADMIN_KEY", "REPLACE_WITH_KAKAOPAY_KEY")
# Replace base urls with PG's actual endpoints
KAKAOPAY_READY_URL = "https://kapi.kakao.com/v1/payment/ready"
KAKAOPAY_APPROVE_URL = "https://kapi.kakao.com/v1/payment/approve"

# DB helper
DB_PATH = os.environ.get("DB_PATH", "payment_codes.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS codes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      code TEXT UNIQUE,
      quota INTEGER,
      created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

def save_code(code, quota):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO codes (code, quota, created_at) VALUES (?, ?, ?)", (code, quota, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_code_row(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT code, quota FROM codes WHERE code = ?", (code,))
    row = c.fetchone()
    conn.close()
    return row

def decrement_code(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE codes SET quota = quota - 1 WHERE code = ?", (code,))
    conn.commit()
    c.execute("SELECT quota FROM codes WHERE code = ?", (code,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else None

@app.route("/create_payment", methods=["POST"])
def create_payment():
    """
    Frontend posts JSON: { 'item_name': '세특100회', 'amount': 5000, 'order_id': '...' }
    This endpoint calls PG READY API (example: KakaoPay) and returns next_redirect_pc_url (or mobile)
    """
    data = request.json or {}
    item_name = data.get("item_name", "세특 문장 생성 100회")
    amount = int(data.get("amount", 5000))
    order_id = data.get("order_id", str(uuid.uuid4()))
    # example payload for KakaoPay (fields vary)
    headers = {
        "Authorization": f"KakaoAK {KAKAOPAY_ADMIN_KEY}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "cid": "TC0ONETIME",  # test cid - replace with store cid for production
        "partner_order_id": order_id,
        "partner_user_id": "user_1",
        "item_name": item_name,
        "quantity": 1,
        "total_amount": amount,
        "tax_free_amount": 0,
        # redirect URLs must be publicly accessible (https)
        "approval_url": os.environ.get("HOST_URL", "https://your-domain.com") + "/payment/approve?order_id=" + order_id,
        "cancel_url": os.environ.get("HOST_URL", "https://your-domain.com") + "/payment/cancel",
        "fail_url": os.environ.get("HOST_URL", "https://your-domain.com") + "/payment/fail",
    }

    # Call PG ready endpoint
    r = requests.post(KAKAOPAY_READY_URL, data=payload, headers=headers, timeout=10)
    if r.status_code != 200:
        return jsonify({"ok": False, "error": r.text, "status_code": r.status_code}), 500
    resp = r.json()
    # resp typically contains: next_redirect_pc_url, tid, ...
    return jsonify({"ok": True, "pg_response": resp})

@app.route("/payment/approve", methods=["GET"])
def payment_approve_redirect():
    """
    This is an example redirect endpoint that the PG will redirect the user to after payment approval.
    KakaoPay approves with query params including pg_token; you must call approve API to confirm payment.
    """
    pg_token = request.args.get("pg_token")
    partner_order_id = request.args.get("order_id")  # if you pass it as query
    tid = request.args.get("tid")
    # You should call the approve API here using tid and pg_token
    headers = {
        "Authorization": f"KakaoAK {KAKAOPAY_ADMIN_KEY}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "cid": "TC0ONETIME",
        "tid": tid,
        "partner_order_id": partner_order_id,
        "partner_user_id": "user_1",
        "pg_token": pg_token
    }
    r = requests.post(KAKAOPAY_APPROVE_URL, data=payload, headers=headers, timeout=10)
    if r.status_code != 200:
        return "결제 확인 실패: " + r.text, 500
    resp = r.json()
    # Payment confirmed. Now generate a code and save it
    code = "CODE-" + uuid.uuid4().hex[:8].upper()
    quota = 100  # 100 uses
    save_code(code, quota)
    # You could show a page or redirect to frontend with code in query string
    # For demo, simple success message
    return f"결제 완료. 이용코드: {code}. 잔여 횟수: {quota}. 복사해서 앱에 입력하세요."

# API for frontend to validate code & get remaining quota
@app.route("/api/code/<code>", methods=["GET"])
def api_get_code(code):
    row = get_code_row(code)
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify({"ok": True, "code": row[0], "quota": row[1]})

# For demo only: issue a test code (admin)
@app.route("/admin/issue_test_code", methods=["POST"])
def admin_issue_test_code():
    # WARNING: in production protect this endpoint!
    new_code = "TEST-100"
    save_code(new_code, 100)
    return jsonify({"ok": True, "code": new_code})

if __name__ == "__main__":
    # Run with HTTPS in production. For dev: flask run (http) or use ngrok to test webhooks
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000")), debug=True)
