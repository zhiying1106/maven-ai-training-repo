from __future__ import annotations

from langchain.agents import create_agent
from langgraph.graph import StateGraph, END

from app.models import get_chat_model, get_judge_model
from app.tools import get_tool_belt

from typing_extensions import TypedDict

class AgentState(TypedDict):
    messages: list
    helpful: bool
    retries: int

MAX_RETRIES = 2

SYSTEM_PROMPT = """
You are a helpful assistant specialized in feline (cat) health. 
Use the retrieve_information tool for cat-health questions, web search for current information, and Arxiv for research papers. 
Cite tool results when they inform your answer.
"""


JUDGE_PROMPT = """"
You are evaluating whether an assistant response is helpful.

Return ONLY one word:

APPROVE
or
RETRY

Assistant response:
{answer}
"""

chat_model = get_chat_model()
judge_model = get_judge_model()

agent = create_agent(
    model=chat_model,
    tools=get_tool_belt(),
    system_prompt=SYSTEM_PROMPT,
)


def _coerce_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for block in value:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if isinstance(text, str):
                    parts.append(text)
            elif getattr(block, "text", None) is not None:
                parts.append(str(block.text))
        return "".join(parts)
    if value is None:
        return ""
    return str(value)


def retrieve_node(state: AgentState):
    """Run the agent."""

    result = agent.invoke(
        {
            "messages": state["messages"],
        }
    )

    return {
        "messages": result["messages"],
    }

def judge_node(state: AgentState):
    """Judge whether the latest response is helpful."""

    answer = _coerce_text(getattr(state["messages"][-1], "content", ""))

    result = judge_model.invoke(
        JUDGE_PROMPT.format(answer=answer)
    )

    decision = _coerce_text(result.content).strip().upper()

    return {
        "helpful": decision == "APPROVE"
    }


def retry_node(state: AgentState):
    """Increment retry counter."""

    return {
        "retries": state.get("retries", 0) + 1
    }


def route_after_judge(state: AgentState):
    if state.get("helpful", False):
        return END

    if state.get("retries", 0) >= MAX_RETRIES:
        return END

    return "retry"

builder = StateGraph(AgentState)

builder.add_node("retrieve", retrieve_node)
builder.add_node("judge", judge_node)
builder.add_node("retry", retry_node)

builder.set_entry_point("retrieve")

builder.add_edge("retrieve", "judge")
builder.add_conditional_edges(
    "judge",
    route_after_judge,
    {
        "retry": "retry",
        END: END,
    },
)

builder.add_edge("retry", "retrieve")

graph = builder.compile()