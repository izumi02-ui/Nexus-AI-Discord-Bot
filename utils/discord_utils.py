"""
Project Nexus

Discord Utilities
"""


async def send_long_message(
    destination,
    content: str,
):

    MAX_LENGTH = 2000

    while len(content) > MAX_LENGTH:

        split = content.rfind(
            "\n",
            0,
            MAX_LENGTH
        )

        if split == -1:
            split = MAX_LENGTH

        await destination.send(
            content[:split]
        )

        content = content[split:].lstrip()

    if content:

        await destination.send(
            content
        )
