"""
Project Nexus

Provider Capabilities

Defines the capabilities of each AI provider.
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
    ):

        self.web_search = web_search
        self.vision = vision
        self.files = files
        self.image_generation = image_generation
        self.code_execution = code_execution
        self.function_calling = function_calling

    def supports(
        self,
        capability: str,
    ) -> bool:

        return getattr(
            self,
            capability,
            False
        )