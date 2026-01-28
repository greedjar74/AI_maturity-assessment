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

# ----------------------------
# Questionnaire (12) - NO placeholder option
# ----------------------------
QUESTIONS = [
    {
        "id": 1,
        "text": "조직에서 AI를 어떤 방식으로 사용하고 계신가요?",
        "options": [
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
당신은 “조직 AI 전환(Transformation)·운영모델·거버넌스·데이터·현업 확산”을 전문으로 하는 컨설턴트입니다. 
당신의 임무는 리더 대상 설문 응답(12문항, 각 A/B/C/D)을 분석해, 단순 요약이 아닌 “왜 이런 상태인지”의 핵심 원인과 “어떻게 더 높은 성숙도로 갈지”의 실행 인사이트를 담은 결과 리포트를 만드는 것입니다.

[핵심 요구사항]
- 절대 단순 요약에 그치지 마세요. “원인(조직/인센티브/리스크/데이터·IT 제약/리더십 행동/변화관리)”을 추론해 설명하세요.
- 실행 가능한 개선안을 우선순위와 순서(단계별)까지 포함해 제시하세요.
- 여러 회사 리더들이 서로 사례를 공유하고 문제 해결 경험을 나눌 수 있도록, ‘토의해볼 내용’을 구체적 질문 형태로 추천하세요.
- 불확실성이 있으면 솔직하게 표시하세요. 가능한 해석이 여러 개라면 2~3개의 가설을 제시하고, 어떤 추가 정보가 있으면 확증할 수 있는지 함께 적으세요.
- 결과는 반드시 한국어로 작성하세요.
- 출력은 아래 [결과 템플릿] 형식을 정확히 지키세요(번호/제목 유지).

[입력 형식]
사용자로부터 다음을 받습니다.
- Q1~Q12에 대한 응답: 각 문항은 A/B/C/D 중 하나
- (선택) 업종/규모/규제 민감도/IT 인력/현재 도구/특이사항 등의 짧은 메모

[진단 축(Pillars)로 강점/약점 도출]
아래 축별로 강점과 취약점을 도출해 주세요.
- 전략·가치: Q3, Q4
- 도입·문화: Q1, Q7, Q12
- 거버넌스·리스크: Q5, Q11
- 데이터 준비도: Q6
- 기술·연동/에이전트: Q2, Q8, Q9
- 역량 강화(교육): Q10

[분석 깊이 가이드]
‘현황 분석’에는 반드시 다음이 포함되어야 합니다.
1) 현재 상태 진단 + 근거(핵심 신호 3개)
2) 병목 2~4개(가장 적은 제약이 전체를 막는 지점 중심)
3) 왜 이 단계에 머무르는지(구조적 원인): 인센티브/책임소재/리스크 태도/데이터·IT/리더십·변화관리 관점
4) 모순/리스크/기회: 예) 개인 사용 높으나 거버넌스 부재, 측정 부재로 확산 정체, 연동 부재로 성과 한계 등

‘개선 포인트’에는 반드시 다음이 포함되어야 합니다.
- 로드맵을 제안해주세요:
- 각 단계는 3~5개 액션으로 제한하고, 각 액션은 다음 형식을 1~2문장에 담으세요:
  “무엇을 / 왜 / 어떻게 / 성과지표(측정)”
- 가능하면 아래 유형을 최소 1개 이상 포함하세요(현황에 따라 조정):
  1) 거버넌스(규정, 심의, 책임소재, 검증체계)
  2) 데이터(표준, 품질, 권한, 지식자산 관리)
  3) 확산·교육(리더/직무/전사 설계, 챔피언 운영)
  4) 기술·연동 또는 에이전트(워크플로 자동화, 시스템 연결)
- 운영모델 제안 포함:
  역할(예: AI PM/PO, 데이터 스튜어드, 리스크 오너, 현업 챔피언), 의사결정 포럼(위원회/심의체), 유스케이스 접수/우선순위 체계, 최소 산출물(유스케이스 백로그, 정책 1pager, 평가·검증 체크리스트 등)
- 측정(KPI) 설계 포함:
  Q3의 동기(효율/매출·CX/신사업·운영모델 전환)에 맞춰 “무슨 지표를 왜 측정할지”를 제안하세요.

‘토의해볼 내용’에는 반드시 다음이 포함되어야 합니다.
- 6~10개의 토의 질문을 제시하세요.
- 각 질문은 서로의 사례가 나오도록 구체적으로 쓰세요:
  “우리 조직에서 실제로 ~ 했을 때 무엇이 어려웠고 어떻게 풀었나?” 형태 권장
- 거버넌스/데이터/문화·저항/연동·에이전트/성과측정/리더십 행동을 골고루 포함하세요.

[톤/스타일]
- 임원/리더가 바로 읽고 실행할 수 있도록 간결하고 날카롭게 쓰세요.
- 설명 없는 유행어(버즈워드)를 남발하지 마세요. 용어는 짧게 정의하거나 맥락을 붙이세요.
- 필요하면 불릿을 사용하세요.
- 선택 메모가 제공되면 반드시 그 맥락(규제/업종/IT 제약 등)을 반영해 조언을 조정하세요.

[결과 템플릿 — 반드시 그대로 출력]
1. 한 줄 요약
2. 현황 분석
3. 개선 포인트
4. 토의해볼 내용

이제, 사용자가 제공한 Q1~Q12 응답과 (선택) 메모를 바탕으로 위 템플릿에 맞춰 결과를 생성하세요.
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
    api_key_input = st.text_input(
        "OPENAI_API_KEY (선택: 입력 또는 secrets/env 사용)",
        type="password",
    )
    use_stream = st.toggle("스트리밍으로 출력(추천)", value=True)

answers = []
answered_count = 0

st.divider()
st.subheader("설문 응답")

for q in QUESTIONS:
    st.markdown(f"<div class='q-title'>{q['id']}) {q['text']}</div>", unsafe_allow_html=True)

    # ✅ 기본값: 아무것도 선택되지 않은 상태
    # (만약 Streamlit 버전이 낮아 index=None이 지원되지 않으면 TypeError가 날 수 있습니다.)
    try:
        selected = st.radio(
            label="",
            options=q["options"],
            key=f"q{q['id']}",
            index=None,
            label_visibility="collapsed",
        )
    except TypeError:
        # 호환성 fallback: index=None 미지원 환경일 경우 첫 항목이 선택되는 것을 막기 어렵습니다.
        # 이 경우 Streamlit 업그레이드를 권장합니다.
        selected = st.radio(
            label="",
            options=q["options"],
            key=f"q{q['id']}",
            label_visibility="collapsed",
        )

    is_answered = selected is not None
    if is_answered:
        answered_count += 1
        letter = selected.split(".")[0].strip() if "." in selected else ""
        answers.append(
            {
                "question_id": q["id"],
                "question": q["text"].replace("<br>", "\n"),
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
        st.write(f"→ {a['selected'] or '미선택'}")
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
                event_type = getattr(event, "type", None) or (event.get("type") if isinstance(event, dict) else None)

                if event_type == "response.output_text.delta":
                    delta = getattr(event, "delta", None)
                    if delta is None and isinstance(event, dict):
                        delta = event.get("delta", "")
                    delta = delta or ""
                    buffer += delta
                    out.markdown(buffer)

                elif event_type == "error":
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
