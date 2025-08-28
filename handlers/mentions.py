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

def show_help(say, user, thread_ts=None):
    try:
        say(
            blocks=[{
                "type":"section",
                "text":{"type":"mrkdwn",
                        "text": "🧭 *사용법*\n- `@OCBIS: 질문: ...`\n예) `@OCBIS: 질문: Nxmile은 무엇인가요`"}
            }],
            text="사용법: @OCBIS 질문: ...",   # ✅ 폴백 텍스트 (한 번만!)
            thread_ts=thread_ts
        )
    except Exception as e:
        say("사용법: @OCBIS 질문: ...", thread_ts=thread_ts)

def register_mentions(app):
    @app.event("app_mention")
    def handle_mention(body, say, context, logger):
        event = body["event"]
        user = event.get("user")
        text = event.get("text", "")
        channel = event.get("channel")
        ts = event.get("thread_ts") or event.get("ts")
        bot_user_id = context.get("bot_user_id")

        question = parse_question(text, bot_user_id)

        if not question:
            logger.info(f"[FALLBACK] user={user} text={text!r} ts={ts} → show_help")
            show_help(say, user, thread_ts=ts)
            return

        logger.info("[LLM_CALL_REQUEST] user=%s channel=%s ts=%s question=%r",
                    user, channel, ts, question)

        # 접수 안내도 스레드로
        say(f"📝 질문 접수: _{question}_\n답변 생성 중…", thread_ts=ts)

        try:
            answer, status = call_agent(question, logger)
            say(blocks=build_answer_blocks(question, answer, status),
                text=f"Q: {question}\n답변: {answer}\n상태: {status}",
                thread_ts=ts)
        except AgentAPIError as e:
            logger.warning(f"AgentAPIError: {e}")
            say(f"⚠️ <@{user}> LLM 호출 중 오류가 발생했어요:\n`{e}`", thread_ts=ts)
        except Exception:
            logger.exception("❌ LLM 호출 중 알 수 없는 예외")
            say("⚠️ 예상치 못한 오류가 발생했어요. 잠시 후 다시 시도해주세요.", thread_ts=ts)