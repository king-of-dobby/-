import streamlit as st
import streamlit.components.v1 as components

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
st.write("학생의 활동 내용을 항목별로 입력하면, ChatGPT에 붙여넣을 수 있는 프롬프트를 자동으로 만들어줍니다.")

# 입력창 3개
activity1 = st.text_area("📝 활동 내용 1", placeholder="예: 독서활동 - '이기적 유전자'를 읽고 토론에 참여함")
activity2 = st.text_area("📝 활동 내용 2", placeholder="예: 실험활동 - 생명과학 실험에서 주도적으로 팀을 이끌며 데이터 정리")
activity3 = st.text_area("📝 활동 내용 3", placeholder="예: 발표활동 - 진로 세미나 발표 준비 과정에서 동료와 협업")

length = st.slider("🔠 원하는 글자 수", min_value=100, max_value=500, value=300, step=50)

# 생성 버튼
if st.button("🎯 프롬프트 생성"):
    all_activities = "\n".join([s for s in [activity1, activity2, activity3] if s.strip()])
    if not all_activities:
        st.warning("최소한 하나 이상의 활동 내용을 입력해주세요.")
    else:
        full_prompt = BASE_PROMPT.format(activity=all_activities, length=length)
        st.success("아래 프롬프트를 ChatGPT에 붙여넣어 주세요 👇")
        st.code(full_prompt, language="markdown")

        # 📋 복사 버튼 추가 (JavaScript)
        components.html(f"""
            <textarea id="prompt" style="position:absolute; left:-9999px;">{full_prompt}</textarea>
            <button onclick="copyPrompt()" style="margin-top:10px;padding:8px 16px;border:none;border-radius:5px;background-color:#4CAF50;color:white;cursor:pointer;">
                📋 프롬프트 복사
            </button>
            <script>
            function copyPrompt() {{
                var copyText = document.getElementById("prompt");
                copyText.select();
                document.execCommand("copy");
                alert("프롬프트가 복사되었습니다! ChatGPT에 붙여넣어 주세요.");
            }}
            </script>
        """, height=80)

        # 다운로드 버튼도 유지
        st.download_button(
            label="⬇️ .txt 파일로 다운로드",
            data=full_prompt,
            file_name="chatgpt_prompt.txt",
            mime="text/plain"
        )
