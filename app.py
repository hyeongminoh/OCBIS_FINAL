import os
import requests
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

##기본 기능 - 태그 받으면 메세지 출력
# @app.event("app_mention")
# def reply(body, say):
#     user_text = body["event"]["text"]
#     print(f"[DEBUG] 사용자 입력: {user_text}")
#     say("📣 불렀어요? 여깄어요! 🙋‍♀️")

# ---------- 멘션 시 버튼 노출 ----------
@app.event("app_mention")
def handle_mention(body,say):
    user = body["event"]["user"]
    say(
        text=f"안녕하세요! <@{user}>님, 무엇을 도와드릴까요?",
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
    say(f"<@{user}> 질문을 입력해주세요!")
 
# ---------- 일반 메시지 → 에이전트 API 호출 ----------
@app.event("message")
def handle_message(body, say):
    try:
        event = body["event"]
        text = (event.get("text") or "").strip()
        user = event.get("user", "")

        # 봇이 보낸 메시지/멘션 토큰 메시지는 무시
        if event.get("bot_id") or text.startswith("<@"):
            return

        logger.info(f"🔍 이벤트 수신: user={user}, text={text}")

        # 에이전트 API 호출 준비
        api_url = os.getenv("AGENT_URL", "http://10.250.37.64:8000/api/chat/v1/test")
        payload = {
            "message": text if text.startswith("[LLM call]") else f"[LLM call] {text}"
        }
        headers = {"Content-Type": "application/json"}

        logger.info(f"📤 API 요청: {payload}")
        resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
        logger.info(f"📥 API 응답코드: {resp.status_code}")

        # 응답 파싱 (JSON/텍스트 둘 다 대응)
        if resp.status_code == 200:
            try:
                data = resp.json()
                answer = (
                    data.get("answer")
                    or data.get("result")
                    or data.get("message")
                    or str(data)
                )
            except ValueError:
                answer = resp.text
        else:
            answer = f"API 오류: {resp.status_code} | {resp.text[:300]}"

        # LangChain 재귀 오류 안내 보강
        if "Recursion limit" in answer:
            answer += (
                "\n\n⚠️ 내부 에이전트가 반복 한도에 걸렸어요. "
                "요청을 더 단순하게 하거나 ‘도구 사용 금지, 최종 답만’ 문구를 포함해 다시 시도해 주세요."
            )

        logger.info(f"🤖 최종 답변: {answer[:300]}")

        # 로그 저장 & 응답
        qa_log.append({"user": user, "question": text, "answer": answer})
        say(f"<@{user}> {answer}")

    except Exception as e:
        logger.exception("❌ 처리 중 예외")
        say("⚠️ 죄송해요. 답변 중 오류가 발생했어요.")
        
    

# ---------- 실행 ----------
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()