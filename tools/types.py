"""
Project Nexus

Tool Types
"""

from enum import Enum


class ToolType(str, Enum):

    WEB_SEARCH = "web_search"

    WEATHER = "weather"

    CALCULATOR = "calculator"

    WIKIPEDIA = "wikipedia"

    GITHUB = "github"

    YOUTUBE = "youtube"

    TRANSLATE = "translate"

    TIME = "time"
