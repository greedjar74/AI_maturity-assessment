import os
import re
import streamlit as st
from openai import OpenAI

# -----------------------------
# 1) 시스템 프롬프트 (요청하신 버전 그대로)
# -----------------------------
SYSTEM_PROMPT = """
[역할/페르소나]
너는 Streamlit 활용 전문가이며, GPT API를 활용한 프롬프트 설계에 특화된 “조직 AI 성숙도 진단” 에이전트다.
대화형(챗) 방식으로 사용자를 안내하며, 질문을 한 번에 하나씩만 제시한다.

[목표]
사용자의 A/B 선택 응답을 기반으로 아래 3개 축의 성향을 진단하고, 최종 조합(예: I-A-T)을 산출한 뒤,
제공된 ‘결과 예시’의 형식(섹션 구조/톤/구성)을 그대로 따라 결과 리포트를 작성한다.
- 축1: 추진 동력(I vs O)
- 축2: 결과 판단/책임(A vs G)
- 축3: 활용 방식(T vs P)

[진행 규칙]
1) 시작 트리거
- 사용자가 “시작” 또는 “start”라고 입력하면 진단을 시작한다.
- 그 전에는 다음만 안내한다:
  - “시작”을 입력하면 진단을 시작합니다.
  - 모든 문항은 A 또는 B로 답합니다(대소문자 무관).
  - 민감정보/개인정보/고객정보 등 비밀 데이터는 입력하지 말라고 안내한다.

2) 질문 방식
- 항상 “딱 1개 문항”만 질문한다. (한 메시지에 여러 문항 금지)
- 각 문항은 아래 형식으로 출력:
  - (진행도) 예: [1/36]
  - 문항 코드와 문항 텍스트
  - 선택지 A/B를 그대로 표시
  - “A 또는 B로 답해주세요.”로 마무리
- 사용자가 A/B 외의 답을 하면:
  - 정중히 다시 안내하고 같은 문항을 재질문한다.
  - (예: “응답을 A 또는 B로만 부탁드려요. 다시 선택해 주세요.”)

3) 점수 집계(내부적으로만 수행)
- 사용자의 각 응답을 해당 축에 누적한다. (사용자에게 점수 계산 과정을 길게 설명하지 않는다.)
- 36문항 전체 답변 후 각 축의 다수 선택으로 최종 값을 결정한다.
- 동점 처리 규칙(반드시 적용):
  1) 시나리오 문항(DS/JS/US: 각 4문항)의 다수로 우선 결정
  2) 그래도 동점이면 더 ‘조직화/거버넌스/프로액티브’ 방향으로 결정: O, G, P
- 최종적으로 (I 또는 O) - (A 또는 G) - (T 또는 P) 형태의 3글자 조합을 만든다.

4) 결과 리포트 생성 규칙
- “결과 예시”의 틀을 그대로 사용해 아래 순서/섹션으로 작성한다:
  1) “(조합) : ‘타입명(한글 별칭)’” 한 줄 제목
  2) 한 줄 요약(조합의 의미를 한 문장으로)
  3) <현황 분석> (불릿 4~6개)
  4) <핵심 문제/리스크> (불릿 3~5개)
  5) <다음 단계로 나아가기 위한 실행 포인트>
     - “2주 내 / 90일 내 / 6개월 내” 3개 소제목 + 각 2~3개 불릿
  6) <토의해볼 내용> 질문 4~6개
- 타입명(별칭)은 조합에 맞게 너가 창의적으로 붙이되, 너무 과장하지 말고 실제 조직 컨설팅 문맥의 이름으로 짓는다.
  - 예: “개인 실험가(산발적 자동화형)” 같은 형태
- 내용은 반드시 “사용자 입력(선택 패턴)”에 근거해 논리적으로 맞춰 쓴다.
- 결과에는 다음을 “짧게” 포함한다:
  - 축별 카운트 요약(예: 추진동력 I 8 / O 4)
  - 최종 조합 및 해석
- 보안/개인정보에 대한 일반적 주의 문구를 과도하지 않게 1회 포함한다.

5) 상태 관리
- 너는 대화 내에서 현재 문항 번호와 사용자의 응답 기록을 정확히 유지한다.
- 이미 답한 문항은 다시 묻지 않는다.
- 사용자가 중간에 “그만”, “중단”, “종료”를 말하면:
  - 진행을 멈추고, 현재까지의 응답 기준으로 “임시 결과(불완전)”를 짧게 제공한 뒤,
  - “원하면 ‘계속’이라고 입력하면 이어서 진행”을 안내한다.

[진단 문항]
(이 시스템 프롬프트는 문항을 포함하지만, 본 앱은 세션상태로 문항을 직접 진행/집계한다.)
"""

# -----------------------------
# 2) 진단 문항 데이터 (36문항)
# -----------------------------
QUESTIONS = [
    # Drive: I vs O (8 + DS 4)
    ("D1", "AI 활용이 늘어난 시작점", "A) 특정 개인/팀이 먼저 써보고 퍼졌다 (I)", "B) 경영진 메시지/전사 과제로 시작됐다 (O)", "drive", "I", "O", False),
    ("D2", "“왜 AI를 해야 하는가?”의 언어", "A) “내 일이 빨라져서”가 주된 이유다 (I)", "B) “전략/경쟁력/전사 KPI”가 주된 이유다 (O)", "drive", "I", "O", False),
    ("D3", "예산/라이선스 의사결정", "A) 팀별/개인별로 필요한 만큼 알아서 쓴다 (I)", "B) 중앙에서 기준을 정해 일괄/공식적으로 제공한다 (O)", "drive", "I", "O", False),
    ("D4", "유스케이스 발굴 방식", "A) 현업이 불편한 지점에서 각자 실험하며 나온다 (I)", "B) 중요 프로세스/핵심 과제에서 우선순위를 정한다 (O)", "drive", "I", "O", False),
    ("D5", "확산 채널", "A) 개인 노하우 공유(구두/메신저/비공식)가 중심 (I)", "B) 교육/커뮤니티/챔피언/CoE 등 공식 채널이 중심 (O)", "drive", "I", "O", False),
    ("D6", "AI 관련 역할 존재 여부", "A) “담당 조직/역할”이 거의 없다 (I)", "B) 최소 한 곳은 AI 추진/운영 역할이 있다 (O)", "drive", "I", "O", False),
    ("D7", "도입의 성공 정의", "A) “누가 잘 쓰는지”와 개인 생산성이 핵심 (I)", "B) “어떤 업무가 바뀌었는지”와 조직 성과가 핵심 (O)", "drive", "I", "O", False),
    ("D8", "실패를 다루는 방식", "A) 개인/팀이 조용히 실패하고 다음 실험으로 넘어간다 (I)", "B) 조직이 실패 원인을 축적해 기준/프로세스를 바꾼다 (O)", "drive", "I", "O", False),

    ("DS1", "전사 확산을 시작한다면 첫 액션은?", "A) 현업 실험 사례를 최대한 모아 “잘 되는 것”부터 보여준다 (I)", "B) 우선 전사 목표/우선순위/로드맵을 정하고 그 아래에서 실행한다 (O)", "drive", "I", "O", True),
    ("DS2", "‘AI 잘 쓰는 사람’이 많아졌을 때 리더의 선택은?", "A) 자율을 유지하되 자발 공유만 장려한다 (I)", "B) 챔피언/표준 템플릿을 만들어 공식 확산 구조를 만든다 (O)", "drive", "I", "O", True),
    ("DS3", "현업 반발(“바쁜데 또 도구?”)이 있을 때", "A) 각 팀에 맞게 자율적으로 쓰게 두고 설득은 최소화 (I)", "B) 한두 개 핵심 업무를 지정해 성과를 내며 설득 (O)", "drive", "I", "O", True),
    ("DS4", "예산이 제한될 때 우선순위", "A) 현업이 원하는 도구를 폭넓게 허용(실험 극대화) (I)", "B) 제한된 도구로 표준화(확산/지원/보안 관리 극대화) (O)", "drive", "I", "O", True),

    # Judgment: A vs G (8 + JS 4)
    ("J1", "AI 결과물 “사용 여부”의 최종 결정권", "A) 담당자가 최종 판단한다 (A)", "B) 조직 기준/승인/검토 체계가 있다 (G)", "judge", "A", "G", False),
    ("J2", "대외 산출물(보도자료/제안서/고객메일)에서", "A) 개인이 주의해서 쓰고 필요 시 상사에게만 공유 (A)", "B) AI 사용 시 필수 검수/로그/승인 규칙이 있다 (G)", "judge", "A", "G", False),
    ("J3", "금지/주의 입력 기준", "A) “상식 선에서 알아서”가 많다 (A)", "B) 구체적인 금지항목/허용범위가 문서로 있다 (G)", "judge", "A", "G", False),
    ("J4", "데이터/보안 사고가 나면", "A) 사용자가 책임지고 조직은 사후 대응 (A)", "B) 예방 체계(정책/툴 제한/모니터링)가 조직에 있다 (G)", "judge", "A", "G", False),
    ("J5", "품질 검증 방식", "A) 결과가 괜찮아 보이면 사용한다 (A)", "B) 출처/근거/검증 체크리스트가 있다 (G)", "judge", "A", "G", False),
    ("J6", "법무/준법/보안 협업 방식", "A) 필요할 때만 사후 자문 (A)", "B) 애초에 룰을 같이 만들고 운영한다 (G)", "judge", "A", "G", False),
    ("J7", "책임 경계(R&R)", "A) “결국 현업 책임”이 기본 (A)", "B) 사용자/검토자/승인자 책임이 구분돼 있다 (G)", "judge", "A", "G", False),
    ("J8", "성과 측정", "A) 개인 체감/팀 내부 만족이 주된 지표 (A)", "B) 조직 KPI/지표(시간/품질/비용/리스크)로 본다 (G)", "judge", "A", "G", False),

    ("JS1", "고위험 업무(고객 정보/가격/계약/인사)를 AI로 다룰 때", "A) 담당자 재량 + 사후 책임 강화(교육/주의) (A)", "B) 사전 규칙 + 승인/검수 체계(가드레일) (G)", "judge", "A", "G", True),
    ("JS2", "“AI가 틀린 답을 내서” 문제가 생겼을 때 재발 방지", "A) 사용자 교육 강화(주의/검증 습관) (A)", "B) 체크리스트/프로세스/툴 제한 등 시스템 개선 (G)", "judge", "A", "G", True),
    ("JS3", "속도가 중요한 조직에서 거버넌스는", "A) 최소 룰만 두고 대부분은 현업 재량 (A)", "B) ‘빠른 승인 루프’를 포함해 거버넌스를 설계 (G)", "judge", "A", "G", True),
    ("JS4", "리더로서 불안이 큰 리스크 1순위는", "A) 사용자가 잘못 판단해서 생기는 품질/신뢰 문제 (A)", "B) 기준 없이 퍼져 통제 불가가 되는 구조적 리스크 (G)", "judge", "A", "G", True),

    # Usage: T vs P (8 + US 4)
    ("U1", "AI가 가장 자주 쓰이는 업무 단계", "A) 문장 다듬기/요약/번역/서식 등 마무리 (T)", "B) 문제정의/대안탐색/구조화/리스크 검토 등 초반 (P)", "use", "T", "P", False),
    ("U2", "입력하는 정보의 깊이", "A) 간단히 요청하고 결과만 받는다 (T)", "B) 맥락/제약/목표를 주고 반복 대화한다 (P)", "use", "T", "P", False),
    ("U3", "산출물의 형태", "A) 문서/메일/보고서 문장 생산이 중심 (T)", "B) 의사결정 옵션/시나리오/논리 구조 생산이 중심 (P)", "use", "T", "P", False),
    ("U4", "AI를 “누가” 쓰는가", "A) 개인 작업 시간에 몰래/조용히 쓴다 (T)", "B) 회의 전/중/후 협업의 일부로 쓰인다 (P)", "use", "T", "P", False),
    ("U5", "AI 결과에 대한 태도", "A) 결과가 괜찮으면 그대로 사용 (T)", "B) 반박/대안/검증 요청을 통해 함께 다듬는다 (P)", "use", "T", "P", False),
    ("U6", "반복성", "A) 단발성 질문이 많다 (T)", "B) 동일 업무에 템플릿/워크플로우로 반복 적용한다 (P)", "use", "T", "P", False),
    ("U7", "업무 영향 범위", "A) 개인 생산성에 주로 영향 (T)", "B) 팀 의사결정/프로세스 변화에 영향 (P)", "use", "T", "P", False),
    ("U8", "“AI를 잘 쓴다”의 정의", "A) 빨리/깔끔하게 문서를 만든다 (T)", "B) 더 나은 판단/선택을 만든다 (P)", "use", "T", "P", False),

    ("US1", "중요한 의사결정 전, AI를 어떻게 쓰겠나?", "A) 내 결론을 정리해 표현을 다듬는 데 쓴다 (T)", "B) 내가 놓친 관점/리스크/대안을 찾는 데 쓴다 (P)", "use", "T", "P", True),
    ("US2", "회의 문화에 AI를 넣는다면", "A) 회의 후 요약/액션아이템 정리에만 사용 (T)", "B) 회의 전 안건 구조화/쟁점 대비/대안 설계에 사용 (P)", "use", "T", "P", True),
    ("US3", "신사업/전략 과제에서", "A) 자료 요약과 문서 작성 지원 위주 (T)", "B) 가설/시나리오/반증 질문을 던지게 한다 (P)", "use", "T", "P", True),
    ("US4", "조직 내 AI 역량을 키운다면", "A) 기능 사용법 중심 교육(프롬프트 기본) (T)", "B) 사고/검증/의사결정 프레임워크 중심 교육 (P)", "use", "T", "P", True),
]

TOTAL_Q = len(QUESTIONS)


# -----------------------------
# 3) 유틸: A/B 정규화
# -----------------------------
def normalize_ab(text: str) -> str | None:
    if not text:
        return None
    t = text.strip().lower()
    # allow: 'a', 'b', 'A', 'B', 'a)', 'b)', 'A.', 'B.' etc.
    m = re.match(r"^\s*([ab])\b", t)
    if m:
        return m.group(1).upper()
    if t in ("a", "b"):
        return t.upper()
    return None


def is_start(text: str) -> bool:
    if not text:
        return False
    return text.strip().lower() in ("시작", "start")


def is_stop(text: str) -> bool:
    if not text:
        return False
    return text.strip() in ("그만", "중단", "종료")


def is_continue(text: str) -> bool:
    if not text:
        return False
    return text.strip() in ("계속", "continue", "재개")


# -----------------------------
# 4) 집계 및 최종 타입 결정(동점 규칙 포함)
# -----------------------------
def compute_axis_result(axis_key: str, answers: dict) -> tuple[str, dict]:
    """
    axis_key: 'drive' | 'judge' | 'use'
    answers: {code: 'A'/'B'}
    returns: (final_letter, counts_detail)
    """
    # collect relevant questions
    axis_q = [q for q in QUESTIONS if q[4] == axis_key]
    # total counts
    counts = {}
    scenario_counts = {}
    # counts by letter (I/O, A/G, T/P)
    for code, _, _, _, _, a_letter, b_letter, is_scenario in axis_q:
        pick = answers.get(code)
        if pick == "A":
            counts[a_letter] = counts.get(a_letter, 0) + 1
            if is_scenario:
                scenario_counts[a_letter] = scenario_counts.get(a_letter, 0) + 1
        elif pick == "B":
            counts[b_letter] = counts.get(b_letter, 0) + 1
            if is_scenario:
                scenario_counts[b_letter] = scenario_counts.get(b_letter, 0) + 1

    # determine which two letters exist for this axis
    letters = sorted(list({q[5] for q in axis_q} | {q[6] for q in axis_q}))
    if len(letters) != 2:
        raise ValueError("Axis letters invalid")
    L1, L2 = letters[0], letters[1]  # order not important
    c1, c2 = counts.get(L1, 0), counts.get(L2, 0)

    # tie-break preference by axis
    tie_prefer = {"drive": "O", "judge": "G", "use": "P"}[axis_key]

    if c1 > c2:
        final = L1
    elif c2 > c1:
        final = L2
    else:
        # tie -> scenario majority
        s1, s2 = scenario_counts.get(L1, 0), scenario_counts.get(L2, 0)
        if s1 > s2:
            final = L1
        elif s2 > s1:
            final = L2
        else:
            final = tie_prefer

    detail = {
        "counts": counts,
        "scenario_counts": scenario_counts,
        "letters": (L1, L2),
    }
    return final, detail


def compute_final_type(answers: dict) -> tuple[str, dict]:
    drive_letter, drive_detail = compute_axis_result("drive", answers)
    judge_letter, judge_detail = compute_axis_result("judge", answers)
    use_letter, use_detail = compute_axis_result("use", answers)

    final_type = f"{drive_letter}-{judge_letter}-{use_letter}"
    return final_type, {"drive": drive_detail, "judge": judge_detail, "use": use_detail}


# -----------------------------
# 5) GPT 호출: 최종 리포트 생성
# -----------------------------
def generate_report(client: OpenAI, model: str, final_type: str, axis_details: dict, answers: dict) -> str:
    # counts summary string
    # drive: I/O, judge: A/G, use: T/P (가능한 키만 표시)
    def fmt_counts(d: dict) -> str:
        parts = []
        for k, v in sorted(d.items()):
            parts.append(f"{k} {v}")
        return " / ".join(parts) if parts else "-"

    drive_counts = fmt_counts(axis_details["drive"]["counts"])
    judge_counts = fmt_counts(axis_details["judge"]["counts"])
    use_counts = fmt_counts(axis_details["use"]["counts"])

    # make a compact answer pattern to help the model reason, without exposing full internal logic
    answer_lines = []
    for i, (code, qtext, a_opt, b_opt, _, _, _, _) in enumerate(QUESTIONS, start=1):
        pick = answers.get(code, "")
        answer_lines.append(f"{i:02d}. {code} = {pick}")

    user_payload = f"""
[진단 완료]
- 최종 조합: {final_type}

[축별 카운트]
- 추진 동력(Drive): {drive_counts}
- 판단/책임(Judgment): {judge_counts}
- 활용 방식(Usage): {use_counts}

[응답 기록(코드=선택)]
{chr(10).join(answer_lines)}

요구사항:
- '결과 예시 형식(강제)'에 맞춰 결과 리포트를 한국어로 작성해줘.
- 내용은 위 응답 패턴에 근거해 설득력 있게 구성해줘.
- 보안/개인정보 주의 문구는 1회만 가볍게 포함해줘.
"""

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ],
        temperature=0.6,
    )
    return resp.choices[0].message.content


# -----------------------------
# 6) Streamlit UI
# -----------------------------
st.set_page_config(page_title="조직 AI 성숙도 진단", page_icon="🤖", layout="centered")
st.title("🤖 조직 AI 성숙도 진단 (대화형)")

with st.sidebar:
    st.header("설정")
    api_key = st.text_input("OPENAI_API_KEY", value=os.getenv("OPENAI_API_KEY", ""), type="password")
    model = st.selectbox("Model", ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-4o"], index=0)
    st.caption("키는 서버에 저장되지 않지만, 배포 시엔 secrets 관리 권장.")
    if st.button("진단 초기화", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# init session
if "messages" not in st.session_state:
    st.session_state.messages = []
if "started" not in st.session_state:
    st.session_state.started = False
if "q_index" not in st.session_state:
    st.session_state.q_index = 0
if "answers" not in st.session_state:
    st.session_state.answers = {}  # code -> 'A'/'B'
if "stopped" not in st.session_state:
    st.session_state.stopped = False
if "final_report" not in st.session_state:
    st.session_state.final_report = None

# show chat history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# helper: ask current question
def render_question(idx: int) -> str:
    code, qtext, a_opt, b_opt, *_ = QUESTIONS[idx]
    return (
        f"[{idx+1}/{TOTAL_Q}] **{code}. {qtext}**\n\n"
        f"{a_opt}\n\n"
        f"{b_opt}\n\n"
        f"✅ **A 또는 B로 답해주세요.**"
    )

# initial assistant message if empty
if len(st.session_state.messages) == 0:
    intro = (
        "안녕하세요! **조직 AI 성숙도 진단**을 대화형으로 진행합니다.\n\n"
        "- 시작하려면 **'시작'** 을 입력해 주세요.\n"
        "- 모든 문항은 **A 또는 B**로 답합니다.\n"
        "- 개인정보/고객정보/기밀 데이터는 입력하지 마세요."
    )
    st.session_state.messages.append({"role": "assistant", "content": intro})
    with st.chat_message("assistant"):
        st.markdown(intro)

# user input
user_text = st.chat_input("메시지를 입력하세요 (예: 시작 / A / B / 중단)")
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # Handle API key missing only when we need final report
    # but also helpful to warn early
    if not api_key and st.session_state.final_report is None:
        warn = "⚠️ 사이드바에 **OPENAI_API_KEY**를 입력하면 최종 리포트를 자동 생성할 수 있어요. (진단 질문 진행 자체는 가능)"
        st.session_state.messages.append({"role": "assistant", "content": warn})
        with st.chat_message("assistant"):
            st.markdown(warn)

    # Stop/continue handling
    if is_stop(user_text):
        st.session_state.stopped = True
        msg = "진단을 잠시 멈췄어요. 원하면 **'계속'** 이라고 입력하면 이어서 진행할게요."
        st.session_state.messages.append({"role": "assistant", "content": msg})
        with st.chat_message("assistant"):
            st.markdown(msg)
        st.stop()

    if st.session_state.stopped and is_continue(user_text):
        st.session_state.stopped = False
        msg = "좋아요, 이어서 진행할게요."
        st.session_state.messages.append({"role": "assistant", "content": msg})
        with st.chat_message("assistant"):
            st.markdown(msg)

    # Start flow
    if not st.session_state.started:
        if is_start(user_text):
            st.session_state.started = True
            st.session_state.q_index = 0
            qmsg = render_question(st.session_state.q_index)
            st.session_state.messages.append({"role": "assistant", "content": qmsg})
            with st.chat_message("assistant"):
                st.markdown(qmsg)
        else:
            msg = "진단을 시작하려면 **'시작'** 이라고 입력해 주세요."
            st.session_state.messages.append({"role": "assistant", "content": msg})
            with st.chat_message("assistant"):
                st.markdown(msg)
        st.stop()

    # If already finished
    if st.session_state.final_report is not None:
        msg = "이미 진단이 완료되었습니다. 다시 하려면 사이드바의 **진단 초기화**를 눌러주세요."
        st.session_state.messages.append({"role": "assistant", "content": msg})
        with st.chat_message("assistant"):
            st.markdown(msg)
        st.stop()

    # Process A/B answer
    ab = normalize_ab(user_text)
    if ab is None:
        # re-ask same question
        qmsg = "응답을 **A 또는 B**로만 부탁드려요. 아래 문항에 다시 선택해 주세요.\n\n" + render_question(st.session_state.q_index)
        st.session_state.messages.append({"role": "assistant", "content": qmsg})
        with st.chat_message("assistant"):
            st.markdown(qmsg)
        st.stop()

    # record answer for current question
    code, *_ = QUESTIONS[st.session_state.q_index]
    st.session_state.answers[code] = ab

    # move next
    st.session_state.q_index += 1

    if st.session_state.q_index < TOTAL_Q:
        qmsg = render_question(st.session_state.q_index)
        st.session_state.messages.append({"role": "assistant", "content": qmsg})
        with st.chat_message("assistant"):
            st.markdown(qmsg)
        st.stop()

    # Finished all questions -> compute + generate report
    final_type, details = compute_final_type(st.session_state.answers)

    # If no API key, show local summary only
    if not api_key:
        summary = (
            f"✅ 모든 문항이 완료되었습니다!\n\n"
            f"**최종 조합(로컬 계산): {final_type}**\n\n"
            f"사이드바에 **OPENAI_API_KEY**를 입력하면, 이 조합을 바탕으로 예시 틀에 맞춘 상세 리포트를 생성해드릴게요."
        )
        st.session_state.messages.append({"role": "assistant", "content": summary})
        with st.chat_message("assistant"):
            st.markdown(summary)
        st.stop()

    client = OpenAI(api_key=api_key)

    with st.chat_message("assistant"):
        with st.spinner("최종 리포트를 생성 중..."):
            report = generate_report(client, model=model, final_type=final_type, axis_details=details, answers=st.session_state.answers)

    st.session_state.final_report = report
    st.session_state.messages.append({"role": "assistant", "content": report})
    with st.chat_message("assistant"):
        st.markdown(report)

# Optional: show progress
if st.session_state.started and st.session_state.final_report is None:
    st.progress(min(st.session_state.q_index / TOTAL_Q, 1.0))
    st.caption(f"진행도: {st.session_state.q_index}/{TOTAL_Q}")
