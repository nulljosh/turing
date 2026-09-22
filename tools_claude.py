"""Samantha asks Claude: the one tool that sends your words off this Mac, to Anthropic's frontier model, for the questions
a 0.5B model cannot think through. It runs only when you name it ("ask claude ..."), the harness asks before every call,
it never reaches a model's menu or MCP, and every answer says it came from Claude.

Needs the official SDK (`.venv/bin/pip install anthropic`) and a credential: ANTHROPIC_API_KEY, or `ant auth login`.
"""
import os

MODEL = os.environ.get("SAMANTHA_CLAUDE_MODEL", "claude-opus-5")
LIMIT = 20000  # characters; a longer question is refused, never silently cut
SYSTEM = ("You are answering one question for Samantha, a small assistant that runs on her user's Mac and asked you because "
          "the question needs more than she can do. Answer in plain language and briefly: a few sentences unless the question "
          "truly needs more. No markdown headers. If you are not sure, say so instead of guessing.")


def ask_claude(question):
    """Ask Claude, Anthropic's frontier model, a question too hard for her and return its answer, marked as Claude's.
    Sends the question off this Mac, so it asks first and runs only when named. Needs the anthropic package and a key."""
    q = question.strip()
    if not q:
        return 'Ask Claude what? Say it like "ask claude why the sky is blue".'
    if len(q) > LIMIT:
        return f"That is too long to send in one go: {len(q):,} characters, and the limit is {LIMIT:,}. Ask about one part at a time."
    try:
        import anthropic
    except ImportError:
        return "To ask Claude I need the anthropic package: run .venv/bin/pip install anthropic, then ask again."
    try:
        client = anthropic.Anthropic()
        # fallbacks "default": if Claude's safety classifiers decline, the API reruns it on the model Anthropic recommends
        response = client.beta.messages.create(
            model=MODEL, max_tokens=16000, system=SYSTEM, output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            messages=[{"role": "user", "content": q}],
        )
    except anthropic.AuthenticationError:
        return "Claude did not accept the API key. Set ANTHROPIC_API_KEY or run ant auth login, then ask again."
    except anthropic.PermissionDeniedError:
        return "That API key is not allowed to use Claude's messages. Check its permissions in the Claude Console."
    except anthropic.RateLimitError:
        return "Claude is rate limiting right now. Try again in a minute."
    except anthropic.APIStatusError as e:
        return f"Claude could not answer just now (error {e.status_code}). Try again later."
    except anthropic.APIConnectionError:
        return "I could not reach Claude. Check the internet connection, then ask again."
    except Exception as e:
        # no credential at all: the SDK raises a TypeError ("Could not resolve authentication method") before any request
        if "authentication" in str(e).lower() or "api_key" in str(e).lower():
            return "To ask Claude I need an Anthropic API key: set ANTHROPIC_API_KEY or run ant auth login, then ask again."
        if isinstance(e, TypeError) and "unexpected keyword" in str(e):  # a package too old for fallbacks or output_config
            return "The anthropic package is too old for this: run .venv/bin/pip install -U anthropic, then ask again."
        return f"Asking Claude failed: {e}"
    if response.stop_reason == "refusal":
        return "Claude declined to answer that one."
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        return "Claude sent back no answer."
    cut = " (Claude hit its length limit, so this is cut short.)" if response.stop_reason == "max_tokens" else ""
    return f"{text}{cut}\n(Answered by Claude, {response.model}, not by me.)"
