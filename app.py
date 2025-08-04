import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])

@app.event("*")
def debug_all_events(body, logger):
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
        text="선택해주세요~",
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"<@{user}> 무엇을 선택하시겠어요?"},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "예"},
                        "action_id": "yes_button"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "아니요"},
                        "action_id": "no_button"
                    },
                ],
            },
        ],
    )

@app.action("yes_button")
def handle_yes(ack, body, say):
    ack()
    user = body["user"]["id"]
    say(f"<@{user}> ✅ 예를 선택하셨어요!")
    
@app.action("no_button")
def handle_no(ack, body, say):
    ack()
    user = body["user"]["id"]
    say(f"<@{user}> ❌ 아니요를 선택하셨어요!")

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
    print("봇이 시작되었습니다. Slack에서 메시지를 보내보세요!")  # 봇 시작 메시지