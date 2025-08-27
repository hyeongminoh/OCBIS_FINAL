import os
import json
from typing import Tuple,Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT = float(os.getenv("AGENT_TIMEOUT", "30"))
DEFAULT_URL = os.getenv("AGENT_URL", "http://10.250.37.64:8000/api/chat/v1/test")

class AgentAPIError(Exception):
    """LLM/에이전트 API 호출 실패 래핑 예외"""

def _session_with_retry() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429,500,502,503,504],
        allowed_methods=["POST","GET"],
        raise_on_status=False,
    )
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

def call_agent(question: str, logger, *,
               url: Optional[str] = None,
               timeout: Optional[float] = None) -> Tuple[str,str]:
    
    """
    에이전트(LLM) API 호출. (answer, status) 반환.
    실패 시 AgentAPIError 발생.
    """

    url = url or DEFAULT_URL
    timeout = timeout or DEFAULT_TIMEOUT

    payload = {"message": f"[LLM call] {question}"}
    headers = {"Content-Type": "application/json"}

    logger.info(f"📤 Agent POST {url}  timeout={timeout}s  payload={json.dumps(payload, ensure_ascii=False)[:200]}")
    try:
        sess = _session_with_retry()
        resp = sess.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        logger.exception("🚨 Agent 연결 예외")
        raise AgentAPIError(f"Agent connection error: {e}") from e
    
    logger.info(f"📥 Agent 응답코드: {resp.status_code}")

    #2xx만 정상 처리
    if not (200 <= resp.status_code < 300):
        preview = resp.text[:300] if resp.text else ""
        raise AgentAPIError(f"Agent HTTP {resp.status_code}: {preview}")
    
    #JSON 파싱
    answer_raw = None
    status_raw = None
    try:
        data = resp.json()
        answer_raw = data.get("answer") or data.get("response") or data.get("result") or data.get("message")
        status_raw = data.get("status") or "success"
    except ValueError:
        #JSON 아니면 text로 대체
        answer_raw = resp.text
        status_raw = "success"

    answer = (str(answer_raw or "")).strip()
    status = (str(status_raw or "")).strip()

    if "Recursion limit" in answer:
        answer += "\n\n⚠️ 내부 에이전트가 반복 한도에 걸렸어요. 요청을 더 단순하게 해주세요."

    # Slack block 텍스트 안전 컷
    MAX_LEN = 2800
    if len(answer) > MAX_LEN:
        answer = answer[:MAX_LEN] + " ..."

    return answer,status
