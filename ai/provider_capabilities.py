"""
Project Nexus

Provider Capabilities
"""


class ProviderCapabilities:

    def __init__(
        self,
        *,
        web_search=False,
        vision=False,
        files=False,
        image_generation=False,
        code_execution=False,
        function_calling=False,
        streaming=False,
        reasoning=False,
        embeddings=False,
        audio=False,
        video=False,
    ):

        self.web_search = web_search
        self.vision = vision
        self.files = files
        self.image_generation = image_generation
        self.code_execution = code_execution
        self.function_calling = function_calling
        self.streaming = streaming
        self.reasoning = reasoning
        self.embeddings = embeddings
        self.audio = audio
        self.video = video

    def supports(
        self,
        capability: str,
    ) -> bool:

        return getattr(
            self,
            capability,
            False,
        )

    def to_dict(
        self,
    ) -> dict:

        return {

            "web_search": self.web_search,
            "vision": self.vision,
            "files": self.files,
            "image_generation": self.image_generation,
            "code_execution": self.code_execution,
            "function_calling": self.function_calling,
            "streaming": self.streaming,
            "reasoning": self.reasoning,
            "embeddings": self.embeddings,
            "audio": self.audio,
            "video": self.video,

        }
