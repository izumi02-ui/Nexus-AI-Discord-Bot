"""
Project Nexus

Google Search Tool
"""

from google import genai
from google.genai import types

from utils.settings import settings
from utils.logger import logger


class GoogleSearchTool:

    def __init__(self):

        self.client = genai.Client(
            api_key=settings.gemini_api_key
        )

    @property
    def name(self):

        return "web_search"

    async def execute(
        self,
        query: str,
    ):

        try:

            response = self.client.models.generate_content(
                model=settings.model,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            google_search=types.GoogleSearch()
                        )
                    ]
                )
            )

            logger.info(
                f"Google Search: {query}"
            )

            return {
                "success": True,
                "content": response.text,
                "error": None,
            }

        except Exception as error:

            logger.exception(
                "Google Search Failed"
            )

            return {
                "success": False,
                "content": None,
                "error": str(error),
            }


google_search = GoogleSearchTool()
