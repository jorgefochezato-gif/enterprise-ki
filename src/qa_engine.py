"""
Q&A Engine — powered by Anthropic Claude
Builds a grounded, citation-aware answer from retrieved context chunks.
"""

import os
from typing import List, Dict, Optional
import anthropic

_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your Codespace secrets or .env file."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are an Enterprise Knowledge Intelligence assistant.
Your job is to answer questions strictly using the provided document excerpts.

Rules:
1. Answer only from the provided context. Never fabricate information.
2. If the context does not contain enough information, say so clearly.
3. Always cite your sources by referencing the document name in [brackets].
4. Be concise, professional, and precise — this is an enterprise environment.
5. If multiple documents contribute to the answer, cite all relevant ones.
6. Structure longer answers with clear headings when appropriate.
7. End with a "Sources:" section listing all documents you drew from.
"""


def build_context_block(chunks: List[Dict]) -> str:
    """Format retrieved chunks into a numbered context block."""
    if not chunks:
        return "No relevant documents found in the knowledge base."

    lines = ["=== RETRIEVED DOCUMENT EXCERPTS ===\n"]
    for i, chunk in enumerate(chunks, 1):
        lines.append(
            f"[{i}] Source: {chunk['source']} "
            f"(relevance: {chunk['relevance']:.0%})\n"
            f"{chunk['content'].strip()}\n"
        )
    return "\n".join(lines)


def answer_question(
    question: str,
    chunks: List[Dict],
    chat_history: Optional[List[Dict]] = None,
    stream: bool = True,
) -> str:
    """
    Send question + context to Claude and return the answer.
    chat_history: list of {"role": "user"|"assistant", "content": str}
    """
    client = get_client()

    context_block = build_context_block(chunks)

    # Build the message history
    messages = []

    # Include prior conversation turns (without old context blocks)
    if chat_history:
        for turn in chat_history[-6:]:   # keep last 3 pairs
            messages.append({"role": turn["role"], "content": turn["content"]})

    # Current question with fresh context
    user_message = f"{context_block}\n\n---\n\nQuestion: {question}"
    messages.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    return response.content[0].text


def stream_answer(
    question: str,
    chunks: List[Dict],
    chat_history: Optional[List[Dict]] = None,
):
    """
    Generator that yields text chunks for Streamlit's st.write_stream().
    """
    client = get_client()
    context_block = build_context_block(chunks)

    messages = []
    if chat_history:
        for turn in chat_history[-6:]:
            messages.append({"role": turn["role"], "content": turn["content"]})

    user_message = f"{context_block}\n\n---\n\nQuestion: {question}"
    messages.append({"role": "user", "content": user_message})

    with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text


def validate_api_key() -> tuple[bool, str]:
    """Quick connectivity check for the settings page."""
    try:
        client = get_client()
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True, "Connected to Claude API ✅"
    except EnvironmentError as e:
        return False, str(e)
    except Exception as e:
        return False, f"API error: {e}"