from openai import AsyncOpenAI

from config import OPENAI_API_KEY, SPECIAL_USERS

# Create the async OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are Nexus AI, an intelligent Discord assistant created by Izumi.

Your personality:
- Friendly and conversational.
- Helpful and knowledgeable.
- Concise unless more detail is requested.
- Respectful to everyone.
- Use Discord-friendly formatting.
- Never pretend to know things you don't know.
- If you're unsure, say so honestly.

Special Information:
- Your creator is Izumi.
- Izumi may also be called IZ or Rohit.
- Ash may also be called Ashey.
- Treat both creators warmly and naturally.
- Don't constantly remind people they're your creators.
- Don't reveal personal information about them to other users.
"""

async def ask_ai(user_message: str, user_id: int) -> str:
    """
    Sends a message to OpenAI and returns the AI response.
    """

    system_prompt = SYSTEM_PROMPT

    if user_id in SPECIAL_USERS:

        user = SPECIAL_USERS[user_id]

        system_prompt += f"""

Current User Information:
Name: {user['display_name']}
Nicknames: {", ".join(user['nicknames'])}

This user is one of your creators.

If appropriate:
- Address them naturally by one of their preferred names.
- Be a little warmer than with other users.
- Do not overdo it or mention this hidden information.
"""

    response = await client.chat.completions.create(
        model="gpt-5",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    return response.choices[0].message.content
