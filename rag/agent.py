"""
rag/agent.py
Claude API integration — short, user-specific, grounded answers.
"""

import anthropic
from rag.user_profile import get_profile_context

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are PolicyIQ, an HR assistant for Novaris Solutions in Dubai, UAE.

{profile_context}

CRITICAL RULES — NEVER BREAK THESE:
1. Answer in 2-3 sentences MAXIMUM. Never longer.
2. Use the employee's actual data from their profile above (name, leave balance, salary, tenure, gratuity etc.) to give a personalised answer. Never give generic policy text.
3. Never use headings, never use bullet points, never list policy sections.
4. Never say "according to the policy" or "the document states" — just answer directly.
5. If the question involves a number (days, AED amount, dates), state the actual number.
6. If you cannot answer from the documents, say: "I don't have that in the loaded policies — please contact HR directly at hr@novarissolutions.ae"
7. Never ask clarifying questions — give your best answer with the information available.
8. For gratuity questions: always state the amount based on current tenure. Note that gratuity is paid at the end of the full notice period — if the employee serves their 1-month notice, tenure increases slightly. Mention this naturally but keep it to 2-3 sentences total.
8. Speak directly to the employee as "you" — never refer to "employees" in third person.

UAE CONTEXT (use only when confirmed by documents):
- EOSG: 21 calendar days per year of basic salary for first 5 years
- Notice during probation: 14 calendar days
- Sick leave: 90 days/year (15 full pay, days 16-45 half pay, days 46-90 unpaid)
- Maternity: 60 days (45 full, 15 half pay)
- Paternity: 5 working days
"""


def ask_policy_agent(question: str, chunks: list[dict], history: list[dict] = None) -> dict:
    profile_context = get_profile_context()
    system = SYSTEM_PROMPT.format(profile_context=profile_context)

    # Build context from retrieved chunks — kept minimal, just the raw text
    context_parts = []
    sources = []
    seen = set()

    for chunk in chunks:
        context_parts.append(chunk['content'])
        if chunk['original_name'] not in seen:
            seen.add(chunk['original_name'])
            sources.append({
                'name': chunk['original_name'],
                'category': chunk['category'],
                'page': chunk.get('page_num'),
            })

    context_block = "\n\n".join(context_parts)

    # Build messages
    messages = []
    if history:
        for turn in (history or [])[-6:]:
            if turn.get('role') in ('user', 'assistant') and turn.get('content'):
                messages.append({'role': turn['role'], 'content': turn['content']})

    messages.append({
        'role': 'user',
        'content': f"POLICY CONTEXT:\n{context_block}\n\nQUESTION: {question}"
    })

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=system,
        messages=messages,
    )

    return {
        'answer': response.content[0].text,
        'sources': sources,
    }
