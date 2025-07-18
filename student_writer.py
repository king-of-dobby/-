import streamlit as st
import fitz  # PyMuPDF for PDF parsing
import pandas as pd
import base64
import tempfile
import subprocess
import os

# -----------------------------
# 공통 프롬프트 틀
# -----------------------------
BASE_PROMPT = '''
너는 고등학교 교사이며, 학생의 활동 내용을 바탕으로 학생부에 들어갈 문장을 작성하는 전문가야.

[조건]
- 문체는 학생부 기록에서 사용되는 교사 관찰형 문체를 사용할 것.
- 학생의 태도, 탐구 역량, 성장, 협업, 성찰 등이 드러나도록 작성할 것.
- 글자 수가 적을 경우 간결히, 많을 경우 풍부하게 서술할 것.
- 주관적인 판단은 배제하되 학생의 장점이 드러나도록 기술할 것.
- 반드시 교사의 시점에서 관찰한 것처럼 작성.

[예시 문장]
- 실험에 열정을 가지고 있으며 동아리 활동에 최선을 다하는 모습은 친구들에게도 긍정적인 영향을 줌.
- 활동 후 자기 평가를 통해 부족한 점을 스스로 돌아보는 등 성찰적인 태도를 보임.

[입력]
- 활동 내용: {activity}
- 원하는 글자 수: {length}자 내외

[출력]
학생부 문장:
'''

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="학생부 문장 생성 프롬프트", layout="centered")

st.title("📄 학생부 문장 생성 프롬프트")
st.write("학생 활동 내용을 입력하거나 파일을 업로드하면, ChatGPT에 붙여넣을 수 있는 프롬프트를 자동으로 만들어줍니다.")

# 텍스트 입력 영역 3개 (세로 배치)
activity1 = st.text_area("📝 활동 내용 1", height=150)
activity2 = st.text_area("📝 활동 내용 2", height=150)
activity3 = st.text_area("📝 활동 내용 3", height=150)

# 파일 업로드
uploaded_file = st.file_uploader("📎 또는 파일 업로드 (pdf, xlsx, hwp)", type=["pdf", "xlsx", "hwp"])
extracted_text = ""

if uploaded_file:
    if uploaded_file.name.endswith(".pdf"):
        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
            for page in doc:
                extracted_text += page.get_text()

    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
        extracted_text = "\n".join(str(cell) for row in df.values for cell in row if pd.notnull(cell))

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
            if os.path.exists(txt_output):
                os.remove(txt_output)

    st.text_area("📖 추출된 텍스트 미리보기", extracted_text, height=200)

# 원하는 글자 수 선택
length = st.slider("🔠 원하는 글자 수", min_value=100, max_value=500, value=300, step=50)

# 프롬프트 생성
if st.button("🎯 프롬프트 생성"):
    combined_activity = "\n".join([t for t in [activity1, activity2, activity3, extracted_text] if t.strip()])
    if not combined_activity.strip():
        st.warning("활동 내용을 입력하거나 파일을 업로드해주세요.")
    else:
        full_prompt = BASE_PROMPT.format(activity=combined_activity.strip(), length=length)
        st.success("✅ 아래 프롬프트를 ChatGPT에 붙여넣어 주세요 👇")
        st.text_area("📋 생성된 프롬프트", full_prompt, height=300, key="prompt_area")

        # 복사 버튼 (JS 사용)
        escaped_prompt = full_prompt.replace("\\", "\\\\").replace("`", "\\`").replace("\n", "\\n").replace("'", "\\'")
        copy_js = f"""
            <script>
                function copyToClipboard(text) {{
                    navigator.clipboard.writeText(text).then(function() {{
                        alert(\"프롬프트가 클립보드에 복사되었습니다!\");
                    }}, function(err) {{
                        alert(\"복사 실패: \" + err);
                    }});
                }}
            </script>
            <button onclick="copyToClipboard(`{escaped_prompt}`)"
                    style="
                        background-color:#4CAF50;
                        border:none;
                        color:white;
                        padding:10px 20px;
                        margin-right:10px;
                        font-size:14px;
                        border-radius:5px;
                        cursor:pointer;">
                📋 프롬프트 복사하기
            </button>
        """
        st.markdown(copy_js, unsafe_allow_html=True)

        # 다운로드 버튼 (텍스트 파일 다운로드)
        b64 = base64.b64encode(full_prompt.encode()).decode()
        download_button = f"""
            <a href="data:text/plain;base64,{b64}" download="chatgpt_prompt.txt"
               style="
                   background-color:#2196F3;
                   color:white;
                   padding:10px 20px;
                   font-size:14px;
                   text-decoration:none;
                   border-radius:5px;
                   ">
               💾 프롬프트 다운로드
            </a>
        """
        st.markdown(download_button, unsafe_allow_html=True)

st.markdown("""
    <div style='text-align: center; font-size: 15px;'>
        Copyright 2025. Yoon Ji Young. All rights reserved. 🌻 
    </div>
""", unsafe_allow_html=True)
