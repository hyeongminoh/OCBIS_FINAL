import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import openai
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])
openai.api_key = os.environ["OPENAI_API_KEY"]
logger = logging.getLogger(__name__)

#질문과 답변 저장용
qa_log = [] #추후 postgre

# 디버깅용 로거
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.event("*")
def debug_all_events(body, logger):
    print("[DEBUG] 모든 이벤트 수신", body)
    logger.info(body)

##기본 기능 - 태그 받으면 메세지 출력
# @app.event("app_mention")
# def reply(body, say):
#     user_text = body["event"]["text"]
#     print(f"[DEBUG] 사용자 입력: {user_text}")
#     say("📣 불렀어요? 여깄어요! 🙋‍♀️")

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

# ✅ 버튼 클릭 시 응답
@app.action("ask_question")
def handle_question_button(ack, body, say):
    ack()
    user = body["user"]["id"]
    say(f"<@{user}> 질문을 입력해주세요!")
 
# 💬 사용자 메시지를 GPT로 보내기   
@app.event("message")
def handle_message(body, say):
    try:
        event = body["event"]
        text = event.get("text", "")
        user = event.get("user", "")

        logger.info(f"🔍 이벤트 수신: {text} from {user}")

        if text.startswith("<@"): #봇 멘션은 패스
            return

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        
        #GPT에게 질문 보내기
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": text}
            ]
        )

        answer = response.choices[0]["message"]["content"]
        logger.info(f"🧠 GPT 응답: {answer}")

        #로그저장
        qa_log.append({"user": user, "question": text, "answer": answer})

        #응답전송
        say(f"<@{user}> {answer}")
        
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        say("⚠️ 죄송해요. 답변 중 오류가 발생했어요.")
        
    

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
    print("봇이 시작되었습니다. Slack에서 메시지를 보내보세요!")  # 봇 시작 메시지