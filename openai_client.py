from openai import AsyncOpenAI

from config import OPENAI_API_KEY

# Create the async OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are Nexus AI, a friendly, intelligent Discord assistant.

Be helpful.
Be concise.
Be respectful.
Use Discord-friendly formatting.
"""

async def ask_ai(user_message: str) -> str:
    """
    Sends a message to OpenAI and returns the AI response.
    """

    response = await client.chat.completions.create(
        model="gpt-5",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    return response.choices[0].message.content
