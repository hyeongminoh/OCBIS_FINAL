import os
import requests
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

from logger_setup import get_logger  # ← 분리한 로깅 모듈 사용

# ---------- 초기화 ----------
load_dotenv()
logger = get_logger(__name__)
logger.info("앱 시작 준비...")

app = App(token=os.environ["SLACK_BOT_TOKEN"])
#openai.api_key = os.environ["OPENAI_API_KEY"]

#질문과 답변 저장용
qa_log = [] #추후 postgre


# 멘션 + 질문: 패턴 (멘션 뒤에 콜론 유무 허용)
# 예) "<@U12345>: 질문: Nxmile은 무엇인가요"

MENTION_QUESTION = re.compile(
    r"""^\s*<@(?P<bot>\w+)>\s*:?\s*질문\s*:\s*(?P<q>.+)""",
    re.IGNORECASE | re.DOTALL
)

# ---------- 멘션 시 버튼 노출 ----------
@app.event("app_mention")
def handle_mention(body, say, context, logger):  # ✅ context를 인자로 받음
    event = body["event"]
    user = event.get("user")
    text = event.get("text", "")
    channel = event.get("channel")
    ts = event.get("thread_ts") or event.get("ts")
    bot_user_id = context.get("bot_user_id")
    
    logger.info(f"[app_mention] user={user}, channel={channel}, ts={ts}, text={text}")
    
    m = MENTION_QUESTION.match(text)

    if m and m.group("bot") == bot_user_id:
        # ✅ '@OCBIS: 질문:' 패턴에만 LLM 호출
        question = (m.group("q") or "").strip()
        if not question:
            say(f"<@{user}> `질문:` 뒤에 내용을 적어주세요.\n예) `@OCBIS: 질문: Nxmile은 무엇인가요`")
            return
        
        # ✅ 여기서 '누가 어떤 질문을 했는지' 로그
        logger.info(
            "[LLM_CALL_REQUEST] user=%s channel=%s ts=%s question=%r",
            user, channel, ts, question
        )

        say(f"📝 질문 접수: _{question}_\n답변 생성 중…", thread_ts=ts)

        try:
            api_url = os.getenv("AGENT_URL", "http://10.250.37.64:8000/api/chat/v1/test")
            payload = {"message": f"[LLM call] {question}"}
            headers = {"Content-Type": "application/json"}

            logger.info(f"📤 API 요청 → {api_url} | payload_keys={list(payload.keys())}")

            resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
            logger.info(f"📥 API 응답코드: {resp.status_code}")

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    answer_raw = data.get("answer") or data.get("response") or data.get("result") or data.get("message") or resp.text
                    status_raw = data.get("status") or "success" if resp.status_code == 200 else f"HTTP {resp.status_code}"

                    answer = str(answer_raw).strip()
                    status = str(status_raw).strip()

                    # 너무 길면 앞부분만 (Slack block 텍스트는 보통 3000자 제한)
                    MAX_LEN = 2800
                    if len(answer) > MAX_LEN:
                        answer = answer[:MAX_LEN] + " …"

                except ValueError:
                    answer = resp.text
            else:
                answer = f"API 오류: {resp.status_code} | {resp.text[:300]}"

            if "Recursion limit" in answer:
                answer += "\n\n⚠️ 내부 에이전트가 반복 한도에 걸렸어요. 요청을 더 단순하게 해주세요."

            blocks = [
                {"type":"divider"},
                {"type":"section","text":{"type":"mrkdwn","text":f"*Q.* {question}"}},
                {"type":"divider"},
                {"type":"section","text":{"type":"mrkdwn","text":f"*A.*\n{answer}"}},
                {"type":"section","text":{"type":"mrkdwn","text":f"*Sts.*\n`{status}`"}},
            ]

            #say(blocks=blocks, text=f"Q: {question}\n답변: {answer}\n상태: {status}")  # fallback 텍스트
            # 최종 답변을 스레드로
            say(blocks=blocks,
            text=f"Q: {question}\n답변: {answer}\n상태: {status}", thread_ts=ts)

        except Exception as e:
            logger.exception("❌ LLM 호출 중 예외")
            say(f"⚠️ <@{user}> LLM 호출 중 오류가 발생했어요. 잠시 후 다시 시도해주세요.")
        return

    # ❔ 패턴이 아니면 '도움말 버튼'만 보여주기
    say(
        text=f"안녕하세요! <@{user}>님, 무엇을 도와드릴까요???",
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"<@{user}> 무엇을 도와드릴까요?"},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "질문하기"},
                        "value": "start_question",
                        "action_id": "ask_question"
                    }
                ]
            }
        ]
    )

# ---------- 버튼 클릭 → 질문 유도 ----------
@app.action("ask_question")
def handle_question_button(ack, body, say):
    ack()
    user = body["user"]["id"]
    logger.info(f"[ask_question] user={user}, action triggered")  # 🔥 로그 추가
    say(f"<@{user}> 질문을 입력해주세요!!")
 
# # ---------- 일반 메시지 → 에이전트 API 호출 ----------
# @app.event("message")
# def handle_message(body, say):
#     try:
#         event = body.get("event", {})
#         text = (event.get("text") or "").strip()
#         user = event.get("user", "")
#         ch_type = event.get("channel_type")
#         subtype = event.get("subtype")

#         # 0) raw 로그로 먼저 확인
#         logger.info(f"[message] ch_type={ch_type} subtype={subtype} user={user} text={text}")

#         # 1) 봇이 보낸 메시지는 무시
#         if event.get("bot_id"):
#             return

#         # 2) 편집/조인 등 시스템 메시지는 스킵
#         if subtype and subtype not in (None, "", "thread_broadcast"):
#             logger.info(f"skip subtype={subtype}")
#             return

#         # 에이전트 API 호출 준비
#         api_url = os.getenv("AGENT_URL", "http://10.250.37.64:8000/api/chat/v1/test")
#         payload = {
#             "message": text if text.startswith("[LLM call]") else f"[LLM call] {text}"
#         }
#         headers = {"Content-Type": "application/json"}

#         logger.info(f"📤 API 요청: {payload}")
#         resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
#         logger.info(f"📥 API 응답코드: {resp.status_code}")

#         # 응답 파싱 (JSON/텍스트 둘 다 대응)
#         if resp.status_code == 200:
#             try:
#                 data = resp.json()
#                 answer = (
#                     data.get("answer")
#                     or data.get("result")
#                     or data.get("message")
#                     or str(data)
#                 )
#             except ValueError:
#                 answer = resp.text
#         else:
#             answer = f"API 오류: {resp.status_code} | {resp.text[:300]}"

#         # LangChain 재귀 오류 안내 보강
#         if "Recursion limit" in answer:
#             answer += (
#                 "\n\n⚠️ 내부 에이전트가 반복 한도에 걸렸어요. "
#                 "요청을 더 단순하게 하거나 ‘도구 사용 금지, 최종 답만’ 문구를 포함해 다시 시도해 주세요."
#             )

#         logger.info(f"🤖 최종 답변: {answer[:300]}")

#         # 로그 저장 & 응답
#         qa_log.append({"user": user, "question": text, "answer": answer})
#         say(f"<@{user}> {answer}")

#     except Exception as e:
#         logger.exception("❌ 처리 중 예외")
#         say("⚠️ 죄송해요. 답변 중 오류가 발생했어요.")
        
    

# ---------- 실행 ----------
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()