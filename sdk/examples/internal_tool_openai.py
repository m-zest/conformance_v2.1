"""How an internal tool calls the gateway with the OpenAI Python SDK.

Two changes compared with calling the provider directly:
  1. base_url points at the gateway, api_key is a gateway application key
  2. each request names the signed-in employee in the X-End-User headers

    pip install openai
    GATEWAY_URL=http://localhost:8000/v1 GATEWAY_KEY=gw_... python internal_tool_openai.py
"""
import os

import openai

client = openai.OpenAI(
    base_url=os.getenv("GATEWAY_URL", "http://localhost:8000/v1"),
    api_key=os.getenv("GATEWAY_KEY", "gw_demo_internal_assistant_local_only"),
)


def ask(prompt: str, *, email: str, name: str, team: str) -> str:
    """email, name and team come from the tool's own session, never from user input."""
    try:
        response = client.chat.completions.create(
            model=os.getenv("MODEL", "simulator-small"),
            messages=[{"role": "user", "content": prompt}],
            extra_headers={"X-End-User": email, "X-End-User-Name": name, "X-End-User-Team": team},
        )
    except openai.PermissionDeniedError as exc:
        # HTTP 403 with type policy_violation: the gateway blocked the request.
        # Show the message to the user. It says what to remove and carries a reference ID.
        return f"Blocked by policy: {exc.body.get('message') if isinstance(exc.body, dict) else exc}"
    return response.choices[0].message.content


if __name__ == "__main__":
    print(ask("Summarise our travel policy in two sentences.",
              email="elena.marchetti@meridian.example", name="Elena Marchetti", team="Finance"))
