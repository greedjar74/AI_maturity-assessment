import os
import json
import streamlit as st
from openai import OpenAI

# ----------------------------
# UI Style (Radio options -> card + selected highlight)
# ----------------------------
CSS = """
<style>
/* Page spacing */
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

/* Selected -> light green (uses :has, supported in modern Chromium) */
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
# Questionnaire
# ----------------------------
PLACEHOLDER = "— 선택해주세요 —"

QUESTIONS = [
    {
        "id": 1,
        "text": "AI를 ‘공식적으로’ 도입했나요?",
        "options": [PLACEHOLDER,
                    "A. 아직 아님",
                    "B. 일부 팀이 자발적으로",
                    "C. 조직 차원에서 도입(정책·가이드 존재)",
                    "D. 전사 전략으로 추진"]
    },
    {
        "id": 2,
        "text": "현재 AI 활용이 가장 활발한 업무 영역은 어디인가요?",
        "options": [PLACEHOLDER,
                    "A. 영업/마케팅",
                    "B. 고객지원",
                    "C. 개발/IT",
                    "D. 인사",
                    "E. 재무",
                    "F. 운영/생산",
                    "G. 기획/전략",
                    "H. 법무/리스크",
                    "I. 기타"]
    },
    {
        "id": 3,
        "text": "AI 사용이 ‘개인 생산성’ 수준을 넘어 ‘업무 프로세스’에 들어갔나요?",
        "options": [PLACEHOLDER,
                    "A. 개인이 쓰는 도구 수준",
                    "B. 팀 작업 일부에 적용",
                    "C. 프로세스 표준에 포함",
                    "D. 프로세스가 AI 중심으로 재설계됨"]
    },
    {
        "id": 4,
        "text": "조직 내 AI 사용 패턴은 어떤가요?",
        "options": [PLACEHOLDER,
                    "A. 검색/요약 중심",
                    "B. 문서작성·기획 보조",
                    "C. 분석·의사결정 보조",
                    "D. 자동화(에이전트/워크플로)까지"]
    },
    {
        "id": 5,
        "text": "AI 활용의 ‘목표’가 명확한가요?",
        "options": [PLACEHOLDER,
                    "A. 호기심/트렌드 대응",
                    "B. 비용 절감(효율)",
                    "C. 매출·고객경험 개선",
                    "D. 신사업/운영모델 전환"]
    },
    {
        "id": 6,
        "text": "AI 활용 성과를 측정하는 방식이 있나요?",
        "options": [PLACEHOLDER,
                    "A. 없다",
                    "B. 사례 기반 정성 평가",
                    "C. KPI 일부로 관리",
                    "D. 실험(A/B)·재무효과까지 체계화"]
    },
    {
        "id": 7,
        "text": "AI 사용에 대한 ‘가이드/정책’이 어느 수준인가요?",
        "options": [PLACEHOLDER,
                    "A. 금지/방치 상태",
                    "B. 최소 규칙만",
                    "C. 역할별 가이드·승인 프로세스",
                    "D. 모니터링·감사 체계 포함"]
    },
    {
        "id": 8,
        "text": "데이터 준비도는 어떤가요?",
        "options": [PLACEHOLDER,
                    "A. 데이터가 흩어져 있고 품질 문제 큼",
                    "B. 핵심 데이터는 있으나 표준화 부족",
                    "C. 표준·품질·권한 체계 있음",
                    "D. AI 학습·활용을 위한 데이터 제품화(데이터 제품/카탈로그)"]
    },
    {
        "id": 9,
        "text": "보안/규제/컴플라이언스 관점의 준비도는?",
        "options": [PLACEHOLDER,
                    "A. 불안해서 제한적 사용",
                    "B. 최소 통제(계정·접근)",
                    "C. 민감정보·저작권·로그 정책 운영",
                    "D. 레드팀/리스크 평가/감사까지 정착"]
    },
    {
        "id": 10,
        "text": "AI 결과물의 품질을 어떻게 관리하나요?",
        "options": [PLACEHOLDER,
                    "A. 개인이 알아서 검증",
                    "B. 중요한 문서만 리뷰",
                    "C. 표준 검증 체크리스트·QA 있음",
                    "D. 자동 평가·모니터링(환각/편향/드리프트)"]
    },
    {
        "id": 11,
        "text": "AI를 ‘빌드’(내부 개발/커스터마이징)하고 있나요, ‘바이’(SaaS/도구 활용) 중심인가요?",
        "options": [PLACEHOLDER,
                    "A. 도구 사용(바이) 위주",
                    "B. 일부 커스터마이징",
                    "C. 내부 유스케이스용 개발",
                    "D. 플랫폼/재사용 가능한 컴포넌트 보유"]
    },
    {
        "id": 12,
        "text": "시스템/업무도구와의 연동 수준은?",
        "options": [PLACEHOLDER,
                    "A. 독립적으로 사용",
                    "B. 문서·메신저 수준 연동",
                    "C. CRM/ERP/헬프데스크 등 핵심 시스템 연동",
                    "D. 엔드투엔드 자동화(워크플로/에이전트)"]
    },
    {
        "id": 13,
        "text": "조직 역량(인재·교육·지원)은 어느 수준인가요?",
        "options": [PLACEHOLDER,
                    "A. 자발적 학습",
                    "B. 기본 교육 제공",
                    "C. 역할별 커리큘럼·CoE(전담조직)",
                    "D. 직무 체계/평가/채용까지 반영"]
    },
    {
        "id": 14,
        "text": "변화관리/문화는 어떤 상태인가요?",
        "options": [PLACEHOLDER,
                    "A. 불신·저항 큼",
                    "B. 일부 열정가 중심",
                    "C. 성공사례 공유·확산 메커니즘",
                    "D. 실험 문화(실패 허용·학습 루프) 정착"]
    },
    {
        "id": 15,
        "text": "AI가 만드는 가치와 리스크를 ‘포트폴리오’로 관리하나요?",
        "options": [PLACEHOLDER,
                    "A. 개별 과제 단위로만",
                    "B. 큰 과제 몇 개만 관리",
                    "C. 전사 유스케이스 포트폴리오·우선순위",
                    "D. 가치(ROI)·리스크(법/보안/윤리)를 함께 운영"]
    },
]

# ----------------------------
# Prompt
# ----------------------------
SYSTEM_PROMPT = """
당신은 기업의 AI 도입/전환을 돕는 컨설턴트입니다.
사용자가 선택한 15개 문항의 응답을 바탕으로 'AI 성숙도'를 진단하고, 실행 가능한 조언을 제공합니다.
사용자의 응답 조합에서 드러나는 특징(예: 개인 생산성 중심 vs 프로세스 내재화, 데이터/거버넌스/보안, 성과측정, 자동화/연동 등)을 정확히 해석하세요.

[출력 형식 - 반드시 준수]
1) 한 줄 요약(조합의 의미를 한 문장으로)
2) <현황 분석> (불릿 4~6개)
3) <핵심 문제/리스크> (불릿 3~5개)
4) <다음 단계로 나아가기 위한 실행 포인트>
- 당장 수행할 수 있는 부분
- 장기적인 관점에서 고려할 부분(예: 데이터 구조화, AI 도입 로드맵, 거버넌스/보안, 품질관리, KPI/실험체계 등)
5) <토의해볼 내용> 질문 4~6개
- 현황의 문제를 다른 조직이 어떻게 풀었는지 묻는 질문, 또는 성공적으로 도입한 경우 '어떻게 설계/확산했는지'를 설명하게 하는 질문을 포함

[톤]
- 한국어, 간결하지만 실무적으로.
- 과도한 일반론 금지. 사용자의 응답에 직접 연결해 근거를 드러내며 작성.
"""

def get_api_key(user_input: str) -> str:
    if user_input and user_input.strip():
        return user_input.strip()
    # Streamlit secrets
    if "OPENAI_API_KEY" in st.secrets:
        return str(st.secrets["OPENAI_API_KEY"]).strip()
    # Env
    return (os.getenv("OPENAI_API_KEY") or "").strip()

def build_payload(extra_context: dict, answers: list[dict]) -> str:
    # GPT에게 "질문+응답"을 그대로 전달 (요구사항)
    payload = {
        "meta": extra_context,
        "responses": answers
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

def call_gpt_analysis(api_key: str, model: str, temperature: float, max_tokens: int, user_payload: str, stream: bool):
    client = OpenAI(api_key=api_key)  # key 없으면 여기서 에러가 납니다(사전에 검증)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"아래 JSON은 설문 문항과 사용자의 선택 결과입니다. 이를 기반으로 진단 결과를 작성하세요.\n\n{user_payload}"}
    ]

    if not stream:
        resp = client.responses.create(
            model=model,
            input=messages,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        return resp.output_text

    # Streaming mode: read response.output_text.delta events
    stream_resp = client.responses.create(
        model=model,
        input=messages,
        temperature=temperature,
        max_output_tokens=max_tokens,
        stream=True,
    )
    return stream_resp  # iterator of events


# ----------------------------
# Streamlit App
# ----------------------------
st.set_page_config(page_title="AI 성숙도 진단", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

st.title("AI 성숙도 진단")
st.markdown('<div class="helper">15개 문항을 선택하면, 선택 결과를 GPT API에 전달하여 템플릿 기반 분석 리포트를 생성합니다.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("설정")

    api_key_input = st.text_input("OPENAI_API_KEY (선택: 입력 또는 secrets/env 사용)", type="password")
    model = st.text_input("모델", value="gpt-4o-mini")
    temperature = st.slider("Temperature", 0.0, 1.2, 0.3, 0.1)
    max_tokens = st.slider("Max output tokens", 400, 2500, 1400, 100)

    use_stream = st.toggle("스트리밍으로 출력(추천)", value=True)

    st.divider()
    st.subheader("추가 정보(선택)")
    org_name = st.text_input("조직/회사명", value="")
    industry = st.text_input("산업/도메인", value="")
    size = st.selectbox("조직 규모", ["", "1~50", "51~200", "201~1000", "1001~5000", "5000+"], index=0)
    goals = st.text_area("AI 도입의 배경/목표(알려주면 정확도가 올라갑니다)", value="", height=120)

# Render questions & collect answers
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

        # Parse letter and text if formatted like "A. ...".
        letter = selected.split(".")[0].strip() if "." in selected else ""
        answers.append({
            "question_id": q["id"],
            "question": q["text"],
            "selected": selected,
            "selected_letter": letter,
        })
    else:
        answers.append({
            "question_id": q["id"],
            "question": q["text"],
            "selected": None,
            "selected_letter": None,
        })

st.divider()
progress = answered_count / len(QUESTIONS)
st.progress(progress, text=f"응답 완료: {answered_count}/{len(QUESTIONS)}")

extra_context = {
    "organization": org_name,
    "industry": industry,
    "org_size": size,
    "user_goals": goals,
}

col1, col2 = st.columns([1, 1])

with col1:
    with st.expander("내가 선택한 응답 요약 보기"):
        for a in answers:
            st.write(f"{a['question_id']}) {a['question']}")
            st.write(f"→ {a['selected'] or PLACEHOLDER}")
            st.write("---")

with col2:
    st.info("모든 문항을 선택하면 ‘분석 결과 생성’ 버튼이 활성화됩니다.")

all_answered = all(a["selected"] is not None for a in answers)
btn_disabled = not all_answered

if st.button("분석 결과 생성", type="primary", disabled=btn_disabled):
    api_key = get_api_key(api_key_input)
    if not api_key:
        st.error("OPENAI_API_KEY가 필요합니다. 사이드바에 입력하거나 secrets/env에 설정하세요.")
        st.stop()

    # Build payload to send to GPT
    user_payload = build_payload(extra_context=extra_context, answers=answers)

    st.subheader("분석 결과")
    placeholder = st.empty()

    try:
        if not use_stream:
            with st.spinner("GPT가 분석 중..."):
                result_text = call_gpt_analysis(
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    user_payload=user_payload,
                    stream=False,
                )
            placeholder.markdown(result_text)
        else:
            # Streaming
            buffer = ""
            stream_iter = call_gpt_analysis(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                user_payload=user_payload,
                stream=True,
            )
            for event in stream_iter:
                # event.type examples: response.created, response.output_text.delta, response.completed, error, ...
                if getattr(event, "type", None) == "response.output_text.delta":
                    delta = getattr(event, "delta", "") or ""
                    buffer += delta
                    placeholder.markdown(buffer)
                elif getattr(event, "type", None) == "error":
                    placeholder.error("스트리밍 중 오류가 발생했습니다.")
            # final render (in case last chunk wasn't delta)
            if buffer.strip():
                placeholder.markdown(buffer)

        st.download_button(
            "결과 다운로드 (.md)",
            data=placeholder.markdown if False else (buffer if use_stream else result_text),
            file_name="ai_maturity_report.md",
            mime="text/markdown",
        )

    except Exception as e:
        st.error(f"API 호출 중 오류: {e}")

else:
    if not all_answered:
        st.warning("아직 선택하지 않은 문항이 있습니다. 모든 문항을 선택하면 결과를 생성할 수 있어요.")
