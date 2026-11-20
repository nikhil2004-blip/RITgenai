"""
agent.py – Conversational virtual librarian agent using Groq LLM tool calling.
"""
from datetime import date
import json
import time
from typing import List, Dict, Any, Tuple

from groq import Groq, BadRequestError, RateLimitError
from config import GROQ_API_KEY, LLM_MODEL
import tools


def run_agent(history: List[Dict[str, str]], member_id: int, member_name: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Run the librarian agent loop with multi-step tool calling.
    Returns (reply_text, tool_trace).
    """
    if not GROQ_API_KEY:
        return (
            "Groq API key is not configured. Please add GROQ_API_KEY to your .env file.",
            []
        )

    client = Groq(api_key=GROQ_API_KEY)
    today_str = date.today().isoformat()

    system_prompt = (
        f"You are LibraMind, the virtual librarian of the college library. Today is {today_str}. "
        f"You are interacting with student {member_name} (ID: {member_id}). "
        "Use tools for every fact about books, loans, fines and policies; never guess or invent books. "
        "Before any issue/return/renew/reserve, first call the tool with confirmed=false, show the summary and ask the user to confirm; "
        "call again with confirmed=true only after the user says yes. "
        "If nothing is found say 'I couldn't find that in our library' and suggest similar books via search. "
        "Reply in the user's language (English, Hindi, Hinglish, Kannada), short and friendly, mention availability and due dates. "
        "For recommendations give 3 books and say why each fits. Library topics only; politely refuse anything else. "
        "When calling tools, omit optional parameters rather than passing null values."
    )

    # Use only last 12 messages from history to keep tokens low
    trimmed_history = history[-12:] if len(history) > 12 else history

    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    for msg in trimmed_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    tool_trace: List[Dict[str, Any]] = []

    def call_groq(msgs: List[Dict[str, Any]], retry_tool_error: bool = True, retry_rate_limit: bool = True):
        try:
            return client.chat.completions.create(
                model=LLM_MODEL,
                messages=msgs,
                tools=tools.TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0.2,
                parallel_tool_calls=False,
            )
        except BadRequestError as e:
            if "tool_use_failed" in str(e).lower():
                if retry_tool_error:
                    time.sleep(0.5)
                    retry_msgs = list(msgs) + [{
                        "role": "user",
                        "content": "Please retry calling the tool with valid parameters. Omit any optional parameters instead of passing null."
                    }]
                    return call_groq(retry_msgs, retry_tool_error=False, retry_rate_limit=retry_rate_limit)
                else:
                    # Fallback to direct conversational completion so student never sees a 400 error
                    return client.chat.completions.create(
                        model=LLM_MODEL,
                        messages=msgs,
                        temperature=0.3
                    )
            raise e
        except RateLimitError as e:
            if retry_rate_limit:
                time.sleep(3)
                return call_groq(msgs, retry_tool_error=retry_tool_error, retry_rate_limit=False)
            raise e

    # Loop up to 5 iterations for multi-step reasoning
    for _ in range(5):
        try:
            response = call_groq(messages)
        except Exception as e:
            err_msg = str(e)
            if "rate_limit" in err_msg.lower():
                return "The library assistant is currently experiencing high demand. Please try again in a few moments.", tool_trace
            return f"I encountered an issue connecting to the library service: {err_msg}", tool_trace

        choice = response.choices[0]
        response_message = choice.message

        # If no tool calls requested, we have our final text reply
        if not response_message.tool_calls:
            return response_message.content or "", tool_trace

        # Append assistant message with tool calls
        messages.append(response_message)

        # Execute each requested tool call
        for tool_call in response_message.tool_calls:
            fn_name = tool_call.function.name
            try:
                fn_args = json.loads(tool_call.function.arguments or "{}")
            except Exception:
                fn_args = {}

            tool_result = tools.dispatch(fn_name, fn_args, member_id)
            tool_trace.append({
                "name": fn_name,
                "args": fn_args,
                "result": tool_result
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result)
            })

    # Return last response content if 5 iterations exhausted
    return response_message.content or "Completed request processing.", tool_trace
