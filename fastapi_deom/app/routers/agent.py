import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agent.memory import chat

from ..schemas.agent import AgentRequest, AgentResponse
from ..schemas.responseCommon import ResponseCommon 
router = APIRouter(
    prefix="/agent",
    tags=["agent"],
)


@router.post("/chat", response_model=ResponseCommon)
def agent_chat(body: AgentRequest):
    text = body.msg.strip()
    if not text:
        raise HTTPException(status_code=400, detail="msg 不能为空")
    try:
        reply = chat(text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="模型调用失败") from exc
    return ResponseCommon.success(data=reply)
