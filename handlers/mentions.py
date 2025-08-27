# handlers/mentions.py
import os
import re
import json

from services.agent import call_agent, AgentAPIError
from slack_sdk.errors import SlackApiError

# --- 정규식 & 파서 ---
MENTION_QUESTION = re.compile(
    r"""^\s*<@(?P<bot>\w+)>\s*:?\s*질문\s*:\s*(?P<q>.+)""",
    re.IGNORECASE | re.DOTALL
)

def parse_question(text: str, bot_user_id: str):
    """@봇 다음에 '질문:'이 오면 질문 문자열을 반환, 아니면 None"""
    m = MENTION_QUESTION.match(text or "")
    if not m or m.group("bot") != bot_user_id:
        return None
    return (m.group("q") or "").strip()


def build_answer_blocks(question: str, answer: str, status: str):
    return[
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Q.* {question}"}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*A.*\n{answer}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Sts.*\n`{status}`"}}
    ]

def show_help(say, user: str, thread_ts: str | None = None):
    try:
        say(
        text="사용법 안내",
        blocks=[{
            "type": "section",
            "text": {"type": "mrkdwn",
                     "text": "🧭 *사용법*\n- `@OCBIS: 질문: ...` 형식으로 물어보세요.\n"
                             "  예) `@OCBIS: 질문: Nxmile은 무엇인가요`"}
        }],
        text="사용법: @OCBIS: 질문: ...",   # ✅ 폴백 텍스트
        thread_ts=thread_ts
        )
    except Exception as e:
        # 블록 실패 시에도 최소 텍스트 송출
        say("사용법: @OCBIS: 질문: ...", thread_ts=thread_ts)

def register_mentions(app):
    #질문 패턴 멘션
    @app.event("app_mention")
    def _debug_app_mention(body, say, logger):
        event = body["event"]
        logger.info(f"[DEBUG app_mention] {json.dumps(event, ensure_ascii=False)}")
        ts = event.get("thread_ts") or event.get("ts")
        # 눈으로 확인용 핑
        say("👀 멘션 감지 (디버그)", thread_ts=ts)
    def handle_question_mention(body,say,context,logger):
        event = body["event"]
        user = event.get("user")
        text = event.get("text", "")
        channel = event.get("channel")
        ts = event.get("thread_ts") or event.get("ts")
        bot_user_id = context.get("bot_user_id")

        question = parse_question(text, bot_user_id)
        if not question:
            return None   # <- 꼭 None 리턴 (이벤트 종료 X)
        
        logger.info("[LLM_CALL_REQUEST] user=%s channel=%s ts=%s question=%r",
                    user, channel, ts, question)
        
        # 접수 안내도 스레드에
        say(f"📝 질문 접수: _{question}_\n답변 생성 중…", thread_ts=ts)

        try:
            answer, status = call_agent(question, logger) #서비스레이어
            blocks = build_answer_blocks(question, answer, status)
            say(blocks=blocks,
                text=f"Q: {question}\n답변: {answer}\n상태: {status}",
                thread_ts=ts)
        except AgentAPIError as e:
            logger.warning(f"AgentAPIError: {e}")
            say(f"⚠️ <@{user}> LLM 호출 중 오류가 발생했어요:\n`{e}`", thread_ts=ts)
        except Exception:
            logger.exception("❌ LLM 호출 중 알 수 없는 예외")
            say(f"⚠️ <@{user}> 예상치 못한 오류가 발생했어요. 잠시 후 다시 시도해주세요.", thread_ts=ts)

    #그 외 멘션은 도움말
    @app.event("app_mention")
    def handle_general_mention(body, say, logger):
        event = body["event"]
        user = event.get("user")
        ts = event.get("thread_ts") or event.get("ts")
        show_help(say, user, thread_ts=ts)