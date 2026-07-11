"""
Project Nexus

Google Search Tool
"""

from google import genai
from google.genai import types

from tools.base import BaseTool

from search.search_result import SearchResult

from utils.logger import logger
from utils.settings import settings


class GoogleSearchTool(BaseTool):

    @property
    def name(self):
        return "google"

    @property
    def description(self):
        return "Google Search"

    @property
    def priority(self):
        return 100

    @property
    def requires_api(self):
        return True

    @property
    def available(self):
        return bool(
            settings.gemini_api_key
        )

    def __init__(self):

        if not self.available:

            raise RuntimeError(
                "Gemini API key missing."
            )

        self.client = genai.Client(
            api_key=settings.gemini_api_key
        )

    async def execute(
        self,
        query: str,
    ):

        try:

            logger.info(
                f"Google Search: {query}"
            )

            response = self.client.models.generate_content(

                model=settings.gemini_model,

                contents=query,

                config=types.GenerateContentConfig(

                    tools=[

                        types.Tool(

                            google_search=types.GoogleSearch()

                        )

                    ]

                ),

            )

            return {

                "success": True,

                "content": response.text,

                "results": [

                    SearchResult(

                        title=query,

                        content=response.text,

                        source="Google",

                        confidence=1.0,

                    )

                ],

            }

        except Exception as error:

            logger.exception(
                "Google Search Failed"
            )

            return {

                "success": False,

                "error": str(error),

                "results": [],

            }


google_search = GoogleSearchTool()
