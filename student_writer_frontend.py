# student_writer_frontend.py
import streamlit as st
import requests
import json
import base64
from streamlit.components.v1 import html

BACKEND_URL = st.secrets.get("BACKEND_URL", None) or st.experimental_get_query_params().get("backend", [None])[0] or "https://your-backend.example.com"

st.set_page_config(page_title="학생부 문장 생성", layout="centered")

st.title("📄 학생부 문장 생성기 (결제 연동 데모)")

st.info("하루 5회 무료로 사용하실 수 있습니다. 회원가입 없이 바로 사용 가능합니다.")

# 이용권 정보 (UI)
st.markdown("""
<div style='border:1px solid #ddd;padding:12px;border-radius:8px;background:#fafafa;'>
<b>세특 문장 생성 100회 이용권</b><br>- 5,000원 (회당 50원)<br>- 기간 제한 없음<br>- 사용하지 않은 횟수 소멸 없음<br>- 자동결제/정기결제 없음
</div>
""", unsafe_allow_html=True)

# 결제 버튼: 백엔드에 결제 세션 생성 요청
if st.button("계속 사용하기 – 100회 이용권 5,000원"):
    # Create order_id for tracking
    order_id = "order-" + base64.b64encode(str(st.time()).encode()).decode()[:12]
    payload = {
        "item_name": "세특 문장 생성 100회",
        "amount": 5000,
        "order_id": order_id
    }
    try:
        r = requests.post(f"{BACKEND_URL}/create_payment", json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        st.error(f"결제 준비 실패: {e}")
    else:
        resp = r.json()
        if resp.get("ok"):
            pg_resp = resp.get("pg_response", {})
            # KakaoPay test returns next_redirect_pc_url
            redirect_url = pg_resp.get("next_redirect_pc_url") or pg_resp.get("next_redirect_url") or pg_resp.get("redirect_url")
            if redirect_url:
                st.success("결제 페이지로 이동합니다. 결제 후 '결제 완료' 안내가 나오면 발급된 코드를 복사해 아래에 등록하세요.")
                st.markdown(f"[결제 페이지 열기]({redirect_url})")
            else:
                st.error("PG 응답에 결제 페이지 URL이 없습니다. 응답 확인 필요.")
        else:
            st.error("백엔드 오류: " + json.dumps(resp))

st.caption("필요하실 때만 결제하시면 됩니다.")

st.markdown("---")
st.subheader("🔑 이용 코드 등록")
code_input = st.text_input("이용 코드 입력")
if st.button("등록하기"):
    if not code_input:
        st.warning("코드를 입력하세요.")
    else:
        try:
            r = requests.get(f"{BACKEND_URL}/api/code/{code_input}", timeout=6)
            if r.status_code == 200:
                j = r.json()
                st.success(f"이용 코드가 등록되었습니다. 남은 사용 횟수 : {j.get('quota')}")
                st.session_state['current_code'] = code_input
                st.session_state['quota'] = j.get('quota')
            else:
                st.error("입력하신 코드가 유효하지 않습니다. 다시 확인해주세요.")
        except Exception as e:
            st.error(f"코드 확인 실패: {e}")

# 활동 입력 (5칸)
st.markdown("### 📝 활동 내용 입력 (최대 5개)")
activities = []
for i in range(1,6):
    activities.append(st.text_area(f"활동 내용 {i}", height=120,key=f"act{i}"))

uploaded_file = st.file_uploader("또는 파일 업로드 (pdf/xlsx/hwp)", type=["pdf","xlsx","hwp"])
extracted_text = ""
if uploaded_file:
    # For simplicity show content size; actual extraction can be handled locally or backend
    st.info("파일 업로드을 감지했습니다. (프론트엔드 파일 파싱은 제한적입니다.)")
    # You could send the file to backend for extraction if wanted.

length = st.slider("원하는 글자 수", 100, 1000, 500, 50)

if st.button("프롬프트 생성"):
    combined = "\n".join([a for a in activities if a.strip()])
    if uploaded_file:
        combined += "\n(첨부파일 포함)"
    if not combined.strip():
        st.warning("활동을 입력하거나 파일을 업로드하세요.")
    else:
        # If a code is registered, reduce quota locally (backend tracks authoritative remaining count)
        if st.session_state.get("current_code"):
            st.session_state['quota'] = st.session_state.get('quota',0) - 1
            st.info(f"이용권에서 1회 차감되었습니다. 남은 횟수: {st.session_state['quota']} (백엔드와 동기화 필요)")
        # Build prompt exactly same as backend BASE_PROMPT expects
        prompt = f"""너는 고등학교 교사이며, 학생의 활동 내용을 바탕으로 학생부에 들어갈 문장을 작성하는 전문가야.

[조건]
- 문체는 학생부에서 사용하는 3인칭 관찰 기반의 교사 서술형 문체를 사용할 것.
- 문장은 교사의 관찰을 바탕으로 서술하는 학생부 문체(3인칭 관찰형)를 사용할 것.
- 아래 핵심 역량 중 2가지 이상이 드러나도록 기술할 것: 자기주도적 학습 태도, 탐구 역량(문제 인식, 실험 수행, 자료 분석 등), 공동체 및 협업 태도, 성찰적 태도.
- ‘매우/극히/지나치게’, ‘문제 있음’, ‘부족함이 큼’, ‘~인 것으로 보임’, ‘~하지 못함’ 등의 표현은 사용하지 말 것.
- 구체적 사례에 기반하여 작성할 것.
- 교사의 관찰을 기반으로 객관적으로 작성.
- 원하는 글자 수: {length}자 내외

활동 내용:
{combined}

위 조건에 맞는 학생부 문장을 작성해줘.
"""
        st.text_area("생성용 프롬프트 (ChatGPT에 붙여넣기)", prompt, height=320)
        # Copy button via simple html (may be limited by browser security)
        escaped = prompt.replace("`","\\`").replace("\n","\\n")
        st.markdown(f"""
            <button onclick="navigator.clipboard.writeText(`{escaped}`)" style="background-color:#4CAF50;border:none;color:white;padding:10px 20px;border-radius:5px;cursor:pointer;">
                📋 프롬프트 복사하기
            </button>
            &nbsp;
            <a href="data:text/plain;base64,{base64.b64encode(prompt.encode()).decode()}" download="chatgpt_prompt.txt" style="background-color:#2196F3;color:white;padding:10px 20px;border-radius:5px;text-decoration:none;">
                💾 프롬프트 다운로드
            </a>
        """, unsafe_allow_html=True)

st.markdown("---")
with st.expander("❓ FAQ"):
    st.write("Q. 무료 사용은 어떻게 적용되나요? A. 하루 5회 자동 충전됩니다.")
    st.write("Q. 이용권은 소멸되나요? A. 소멸되지 않습니다.")
    st.write("Q. 결제 방법? A. 카카오페이/네이버페이 연동 (백엔드 필요)")
