import streamlit as st
from streamlit.components.v1 import html
import fitz  # PyMuPDF for PDF parsing
import pandas as pd
import base64
import tempfile
import subprocess
import os

# -----------------------------
# 결제/이용권 데이터 저장용 (간단 버전)
# -----------------------------
if "codes" not in st.session_state:
    st.session_state.codes = {}  # {"코드": 남은횟수}

if "current_code" not in st.session_state:
    st.session_state.current_code = None

# -----------------------------
# 공통 프롬프트 틀
# -----------------------------
BASE_PROMPT = '''
너는 고등학교 교사이며, 학생의 활동 내용을 바탕으로 학생부에 들어갈 문장을 작성하는 전문가야.

[조건]
- 문체는 학생부에서 사용하는 3인칭 관찰 기반의 교사 서술형 문체를 사용할 것.
- 아래 핵심 역량 중 2가지 이상이 드러나도록 기술할 것:
  • 자기주도적 학습 태도
  • 탐구 역량(문제 인식, 실험 수행, 자료 분석 등)
  • 공동체 및 협업 태도
  • 성찰적 태도
- ‘열심히 함’과 같은 모호한 서술을 피하고, 실제 사례 기반으로 구체적으로 작성할 것.
- 감정적·주관적 판단 금지(예: 훌륭함, 뛰어남 등).
- **사용 금지 문구**: ‘매우/극히/지나치게’, ‘문제 있음’, ‘부족함이 큼’, ‘~인 것으로 보임’, ‘~하지 못함’ 등
- 교사의 관찰을 기반으로 객관적으로 작성.

[입력]
- 활동 내용: {activity}
- 원하는 글자 수: {length}자 내외

[출력]
위 조건에 맞는 학생부 문장을 작성해줘.
'''

# -----------------------------
# 복사 버튼 함수
# -----------------------------
def render_copy_button(prompt_text):
    escaped = prompt_text.replace("`", "\`").replace("
", "\n")
    button_code = f"""
    <button onclick="navigator.clipboard.writeText(`{escaped}`)"
        style="background-color:#4CAF50;border:none;color:white;padding:10px 20px;font-size:14px;border-radius:5px;cursor:pointer;">
        📋 프롬프트 복사하기
    </button>
    """
    html(button_code)

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="학생부 문장 생성 프롬프트", layout="centered")

st.title("📄 학생부 문장 생성 프롬프트")
st.write("### 하루 5회 무료로 사용하실 수 있습니다. 회원가입 없이 바로 사용 가능합니다.")

# -----------------------------
# 이용권 안내 박스
# -----------------------------
st.markdown(
    """
    <div style='border:2px solid #ddd; padding:15px; border-radius:10px; background:#fafafa;'>
        <b>🎟️ 세특 문장 생성 100회 이용권</b><br>
        - 5,000원 (회당 50원)<br>
        - 기간 제한 없음<br>
        - 사용하지 않은 횟수 소멸 없음<br>
        - 자동결제/정기결제 없음
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# 결제 버튼
# -----------------------------
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 💳 결제하기")

pay_clicked = st.button("계속 사용하기 – 100회 이용권 5,000원")

if pay_clicked:
    st.info("결제가 완료되면 이용 코드가 바로 발급됩니다. 아래 입력창에 코드를 입력하시면 즉시 사용 가능합니다.")
    st.warning("⚠️ 결제 기능은 카카오페이/네이버페이가 연결된 외부 결제 서버가 필요합니다. 실제 금전 거래는 Streamlit만으로 불가능하며, 별도 결제 연동 서버를 구축해야 합니다.")

st.caption("필요하실 때만 결제하시면 됩니다.")

# -----------------------------
# 이용 코드 입력
# -----------------------------
st.markdown("### 🔑 이용 코드 등록")
input_code = st.text_input("이용 코드 입력")
register = st.button("등록하기")

if register:
    if input_code in st.session_state.codes:
        st.session_state.current_code = input_code
        st.success(f"이용 코드가 등록되었습니다. 남은 사용 횟수 : {st.session_state.codes[input_code]}회")
    else:
        st.error("입력하신 코드가 유효하지 않습니다. 다시 확인해주세요.")

# -----------------------------
# 텍스트 입력 5개
# -----------------------------
st.markdown("### 📝 활동 내용 입력")
activity1 = st.text_area("활동 내용 1", height=120)
activity2 = st.text_area("활동 내용 2", height=120)
activity3 = st.text_area("활동 내용 3", height=120)
activity4 = st.text_area("활동 내용 4", height=120)
activity5 = st.text_area("활동 내용 5", height=120)

# -----------------------------
# 파일 업로드
# -----------------------------
uploaded_file = st.file_uploader("📎 또는 파일 업로드 (pdf, xlsx, hwp)", type=["pdf", "xlsx", "hwp"])
extracted_text = ""

if uploaded_file:
    if uploaded_file.name.endswith(".pdf"):
        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
            for page in doc:
                extracted_text += page.get_text()

    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
        extracted_text = "
".join(str(cell) for row in df.values for cell in row if pd.notnull(cell))

    elif uploaded_file.name.endswith(".hwp"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".hwp") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        txt_output = tmp_path.replace(".hwp", ".txt")
        try:
            subprocess.run(["hwp5txt", tmp_path, txt_output], check=True)
            with open(txt_output, "r", encoding="utf-8", errors="ignore") as f:
                extracted_text = f.read()
        except Exception as e:
            st.error(f"HWP 파일 처리 중 오류 발생: {e}")
        finally:
            os.remove(tmp_path)
            if os.path.exists(txt_output): os.remove(txt_output)

    st.text_area("📖 추출된 텍스트", extracted_text, height=180)

# 원하는 글자 수
length = st.slider("🔠 원하는 글자 수", 100, 1000, 500, 50)

# -----------------------------
# 프롬프트 생성
# -----------------------------
if st.button("🎯 프롬프트 생성"):
    combined_activity = "
".join([
        t for t in [activity1, activity2, activity3, activity4, activity5, extracted_text] if t.strip()
    ])

    if not combined_activity:
        st.warning("활동 내용을 입력하거나 파일을 업로드해주세요.")
    else:
        # 이용권 체크
        if st.session_state.current_code:
            st.session_state.codes[st.session_state.current_code] -= 1
            remaining = st.session_state.codes[st.session_state.current_code]
            st.info(f"이용권 사용 1회 차감! 남은 횟수: {remaining}회")
            if remaining <= 0:
                del st.session_state.codes[st.session_state.current_code]
                st.session_state.current_code = None
                st.error("이용권 사용량이 모두 소진되었습니다.")

        full_prompt = BASE_PROMPT.format(activity=combined_activity, length=length)

        st.success("👇 아래 프롬프트를 ChatGPT에 붙여넣어 주세요")
        st.text_area("📋 생성된 프롬프트", full_prompt, height=300, key="prompt_area")

        render_copy_button(full_prompt)

        # 다운로드
        b64 = base64.b64encode(full_prompt.encode()).decode()
        st.markdown(
            f"""
            <a href="data:text/plain;base64,{b64}" download="chatgpt_prompt.txt"
               style="background-color:#2196F3;color:white;padding:10px 20px;font-size:14px;border-radius:5px;text-decoration:none;">
               💾 프롬프트 다운로드
            </a>
            """,
            unsafe_allow

st.markdown("""
    <div style='text-align: center; font-size: 15px;'>
        Copyright 2025. Yoon Ji Young. All rights reserved. 🌻 
    </div>
""", unsafe_allow_html=True)
