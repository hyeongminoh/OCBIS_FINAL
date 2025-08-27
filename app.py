import os
import re
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from logger_setup import get_logger
from handlers.mentions import register_mentions

load_dotenv()
logger = get_logger(__name__)
logger.info("앱 시작 준비...")

app = App(token=os.environ["SLACK_BOT_TOKEN"])

#멘션 리스너 등록
register_mentions(app)

#버튼 액션은 여기 유지(도움말 버튼)
@app.action("ask_question")
def handle_quenstion_button(ack, body, say, logger):
    ack()
    user = body["user"]["id"]
    say(
        blocks=[{
            "type": "section",
            "text": {"type": "mrkdwn",
                     "text": "🧭 *사용법*\n- 멘션 + 질문 형식으로 물어보세요.\n"
                             "  예) `@OCBIS: 질문: Nxmile은 무엇인가요`\n"
                             "- `질문:` 키워드가 없으면 LLM을 호출하지 않습니다."}
        }],
        text="사용법: @OCBIS: 질문: ..."
    )

@app.event("message")
def _ignore_all_messages(body, logger):
    return None

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()