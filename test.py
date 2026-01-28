import os
import json
import streamlit as st
from openai import OpenAI

# ----------------------------
# UI Style (Radio options -> card + selected highlight)
# ----------------------------
CSS = """
<style>
.main .block-container { padding-top: 2rem; padding-bottom: 3rem; }

/* Big bold question */
.q-title{
  font-size: 1.35rem;
  font-weight: 800;
  margin: 1.35rem 0 0.5rem 0;
  line-height: 1.4;
}

/* Radio option card style */
div[data-testid="stRadio"] > div[role="radiogroup"] label[data-baseweb="radio"]{
  border: 1px solid #D0D7DE;
  border-radius: 14px;
  padding: 10px 12px;
  margin: 8px 0;
  width: 100%;
  background: white;
}

/* Selected -> light green */
div[data-testid="stRadio"] > div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked){
  background: #DFF5E1;
  border-color: #76C893;
}

/* Option font size */
div[data-testid="stRadio"] > div[role="radiogroup"] label[data-baseweb="radio"] span{
  font-size: 1.05rem;
}

/* Small helper text */
.helper { color: #6b7280; font-size: 0.95rem; margin-top: 0.2rem; }
</style>
"""

PLACEHOLDER = "— 선택해주세요 —"

# ----------------------------
# UPDATED Questionnaire (12)
# ----------------------------
QUESTIONS = [
    {
        "id": 1,
        "text": "조직에서 AI를 어떤 방식으로 사용하고 계신가요?",
        "options": [
            PLACEHOLDER,
            "A. 사용이 제한되어 있음",
            "B. 개인적으로 사용중",
            "C. 조직 차원에서 적극적 도입중",
            "D. 전사 AI 혁신을 진행중",
        ],
    },
    {
        "id": 2,
        "text": "조직에서 AI 에이전트를 활용하고 있나요?<br>(AI Agent: AI가 스스로 업무 맥락을 이해하고, 순서에 맞게 처리하여 사용자가 원하는 결과를 생성하는 AI 도구, 일반적으로 챗봇 형식으로 구성되어 있음)",
        "options": [
            PLACEHOLDER,
            "A. 사용하지 않음",
            "B. 개인적으로 사용 중",
            "C. 팀 작업 일부에 적용",
            "D. 업무 프로세스를 AI 중심으로 재설계중",
        ],
    },
    {
        "id": 3,
        "text": "조직에서 AI를 활용하고 있는 ‘이유’가 무엇인가요?",
        "options": [
            PLACEHOLDER,
            "A. 호기심/트렌드 대응",
            "B. 비용 절감(효율)",
            "C. 매출·고객경험 개선",
            "D. 신사업/운영모델 전환",
        ],
    },
    {
        "id": 4,
        "text": "조직에서 AI 활용 성과를 측정하는 방식이 있나요?",
        "options": [
            PLACEHOLDER,
            "A. 없다",
            "B. 사례 기반 정성 평가",
            "C. KPI 일부로 관리",
            "D. 효율화 정도 및 재무효과 측정",
        ],
    },
    {
        "id": 5,
        "text": "조직에서 AI를 안전하게 사용하기 위해 제작된 ‘가이드라인 혹은 거버넌스’가 있나요?",
        "options": [
            PLACEHOLDER,
            "A. 문서화된 공식 기준이 없음",
            "B. 최소한의 규칙(민감정보, 저작권 등)이 존재하지만 심의 프로세스는 존재하지 않음",
            "C. 심의 주체/절차가 정의되어 있고 실제로 운영되고 있음",
            "D. 전사 차원의 모니터링 또는 정기 점검/감사 체계가 존재하며 운영되고 있음",
        ],
    },
    {
        "id": 6,
        "text": "AI 활용을 위해 데이터를 체계적으로 준비하고 있나요?",
        "options": [
            PLACEHOLDER,
            "A. 데이터가 흩어져 있고 품질 문제 큼",
            "B. 핵심 데이터는 있으나 표준화 부족",
            "C. 표준·품질·권한 체계 있음",
            "D. AI 학습 및 활용을 위한 데이터 준비 완료",
        ],
    },
    {
        "id": 7,
        "text": "조직 내 AI 도입 및 활용에 대한 반응은 어떤가요?",
        "options": [
            PLACEHOLDER,
            "A. 불신 혹은 저항이 느껴짐",
            "B. 큰 반응 없음",
            "C. 일부 구성원 자발적 활용",
            "D. 전사적 AI 확산 문화 정착",
        ],
    },
    {
        "id": 8,
        "text": "조직에서 AI 제품을 구매해서 사용하고 계신가요? AI를 직접 개발 해서 사용하고 계신가요?",
        "options": [
            PLACEHOLDER,
            "A. 조직에서 구매/개발 모두 사용하지 않음(구성원 개인 사용)",
            "B. 일부 AI 제품 구입 or 구성원 구매 비용 제공",
            "C. 일부 커스터마이징",
            "D. 자체 플랫폼 개발",
        ],
    },
    {
        "id": 9,
        "text": "현재 조직에서 AI와 시스템/업무 도구의 연동 수준은 어느정도 인가요?",
        "options": [
            PLACEHOLDER,
            "A. AI를 독립적으로 사용",
            "B. 문서·메신저 수준 연동",
            "C. CRM/ERP/헬프데스크 등 핵심 시스템 연동",
            "D. 엔드투엔드 자동화(워크플로/에이전트)",
        ],
    },
    {
        "id": 10,
        "text": "조직의 AI 역량 강화를 AI 교육을 지원하고 있으신가요?",
        "options": [
            PLACEHOLDER,
            "A. 자발적 학습",
            "B. 전사 구성원 교육 중",
            "C. 일부 특정 직급 교육중(예. 리더교육)",
            "D. 일부 특정 직무 교육중 (예. IT 직군만 교육)",
        ],
    },
    {
        "id": 11,
        "text": "팀원 혹은 부하직원의 업무 산출물에 대하여 AI를 정확하게 활용하였는지에 대한 검증을 하고 계십니까?",
        "options": [
            PLACEHOLDER,
            "A. AI 활용을 인지하지 못하고 있었음",
            "B. 검증의 필요성은 느끼지만 실행하고 있지 않음",
            "C. 개인적인 검증 프로세스를 가지고 있음",
            "D. 조직에서 가이드라인 혹은 기술을 가지고 있음",
        ],
    },
    {
        "id": 12,
        "text": "본인의 AI 활용 정도는 어느 정도 입니까?",
        "options": [
            PLACEHOLDER,
            "A. 사용하지 않음",
            "B. GPT, Gemini, Copilot을 활용한 자료 검색에 활용",
            "C. AI Agent 만들어서 이용 가능",
            "D. Workflow 및 자동화 제작 가능",
        ],
    },
]

# ----------------------------
# Prompt
# ----------------------------
SYSTEM_PROMPT = """
당신은 기업의 AI 도입/전환을 돕는 컨설턴트입니다.
사용자가 선택한 설문 응답을 바탕으로 'AI 성숙도'를 진단하고, 실행 가능한 조언을 제공합니다.
응답 조합에서 드러나는 특징(개인 사용 vs 조직 도입, 에이전트/자동화, 성과측정, 거버넌스/보안, 데이터 준비, 문화/교육, 검증체계, 시스템 연동 등)을 정확히 해석하세요.

[출력 형식 - 반드시 준수]
1) 한 줄 요약(조합의 의미를 한 문장으로)
2) <현황 분석> (불릿 4~6개)
3) <핵심 문제/리스크> (불릿 3~5개)
4) <다음 단계로 나아가기 위한 실행 포인트>
- 당장 수행할 수 있는 부분
- 장기적인 관점에서 고려할 부분(예: 데이터 구조화, AI 도입 로드맵, 거버넌스/보안, 품질관리, KPI/실험체계 등)
5) <토의해볼 내용> 질문 4~6개

[톤]
- 한국어, 간결하지만 실무적으로.
- 과도한 일반론 금지. 사용자의 응답에 직접 연결해 근거를 드러내며 작성.
"""

# ----------------------------
# Fixed model settings (no UI)
# ----------------------------
MODEL = "gpt-4o-mini"
TEMPERATURE = 0.3
MAX_OUTPUT_TOKENS = 1400


def get_api_key(user_input: str) -> str:
    if user_input and user_input.strip():
        return user_input.strip()
    if "OPENAI_API_KEY" in st.secrets:
        return str(st.secrets["OPENAI_API_KEY"]).strip()
    return (os.getenv("OPENAI_API_KEY") or "").strip()


def build_payload(answers: list[dict]) -> str:
    payload = {"responses": answers}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def call_gpt_analysis(api_key: str, user_payload: str, stream: bool):
    client = OpenAI(api_key=api_key)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "아래 JSON은 설문 문항과 사용자의 선택 결과입니다. "
                "이를 기반으로 진단 결과를 작성하세요.\n\n"
                f"{user_payload}"
            ),
        },
    ]

    if not stream:
        resp = client.responses.create(
            model=MODEL,
            input=messages,
            temperature=TEMPERATURE,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        return resp.output_text

    return client.responses.create(
        model=MODEL,
        input=messages,
        temperature=TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        stream=True,
    )


# ----------------------------
# Streamlit App
# ----------------------------
st.set_page_config(page_title="AI 성숙도 진단", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

st.title("AI 성숙도 진단")
st.markdown(
    "<div class='helper'>12개 문항을 선택하면, 선택 결과를 GPT API에 전달하여 템플릿 기반 분석 리포트를 생성합니다.</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("설정")
    api_key_input = st.text_input("OPENAI_API_KEY (선택: 입력 또는 secrets/env 사용)", type="password")
    use_stream = st.toggle("스트리밍으로 출력(추천)", value=True)

answers = []
answered_count = 0

st.divider()
st.subheader("설문 응답")

for q in QUESTIONS:
    st.markdown(f"<div class='q-title'>{q['id']}) {q['text']}</div>", unsafe_allow_html=True)

    selected = st.radio(
        label="",
        options=q["options"],
        key=f"q{q['id']}",
        label_visibility="collapsed",
    )

    is_answered = selected != PLACEHOLDER
    if is_answered:
        answered_count += 1
        letter = selected.split(".")[0].strip() if "." in selected else ""
        answers.append(
            {
                "question_id": q["id"],
                "question": q["text"].replace("<br>", "\n"),  # 저장용은 줄바꿈으로
                "selected": selected,
                "selected_letter": letter,
            }
        )
    else:
        answers.append(
            {
                "question_id": q["id"],
                "question": q["text"].replace("<br>", "\n"),
                "selected": None,
                "selected_letter": None,
            }
        )

st.divider()
progress = answered_count / len(QUESTIONS)
st.progress(progress, text=f"응답 완료: {answered_count}/{len(QUESTIONS)}")

all_answered = all(a["selected"] is not None for a in answers)

with st.expander("내가 선택한 응답 요약 보기"):
    for a in answers:
        st.write(f"{a['question_id']}) {a['question']}")
        st.write(f"→ {a['selected'] or PLACEHOLDER}")
        st.write("---")

if st.button("분석 결과 생성", type="primary", disabled=not all_answered):
    api_key = get_api_key(api_key_input)
    if not api_key:
        st.error("OPENAI_API_KEY가 필요합니다. 사이드바에 입력하거나 secrets/env에 설정하세요.")
        st.stop()

    user_payload = build_payload(answers)

    st.subheader("분석 결과")
    out = st.empty()

    try:
        if not use_stream:
            with st.spinner("GPT가 분석 중..."):
                result_text = call_gpt_analysis(api_key=api_key, user_payload=user_payload, stream=False)
            out.markdown(result_text)
            final_text = result_text
        else:
            buffer = ""
            stream_iter = call_gpt_analysis(api_key=api_key, user_payload=user_payload, stream=True)
            for event in stream_iter:
                if getattr(event, "type", None) == "response.output_text.delta":
                    delta = getattr(event, "delta", "") or ""
                    buffer += delta
                    out.markdown(buffer)
                elif getattr(event, "type", None) == "error":
                    out.error("스트리밍 중 오류가 발생했습니다.")
            if buffer.strip():
                out.markdown(buffer)
            final_text = buffer

        st.download_button(
            "결과 다운로드 (.md)",
            data=final_text,
            file_name="ai_maturity_report.md",
            mime="text/markdown",
        )

    except Exception as e:
        st.error(f"API 호출 중 오류: {e}")

else:
    if not all_answered:
        st.warning("아직 선택하지 않은 문항이 있습니다. 모든 문항을 선택하면 결과를 생성할 수 있어요.")