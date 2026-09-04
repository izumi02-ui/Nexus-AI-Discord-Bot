"""
Project Nexus

Test configuration

Tests run offline, against a throwaway database, with the network disabled.

The network guard is the important part: the accuracy pipeline is allowed to
degrade when an API is unreachable, and the only way to prove that is to make
unreachability the default in tests. A test that needs a tool's output builds a
SearchResult fixture instead of calling the API.
"""

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_TMP = pathlib.Path(tempfile.mkdtemp(prefix="nexus-tests-"))

os.environ["DATABASE_NAME"] = str(_TMP / "nexus-test.db")
os.environ["SELF_UPDATE_ENABLED"] = "false"
os.environ["MODEL_AUTO_REFRESH"] = "false"
os.environ["BRIDGE_API_KEY"] = ""
os.environ["OPENROUTER_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    from database.database import setup_database

    setup_database()

    yield

    import shutil

    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Any real outbound call in a test is a bug - fail loudly instead."""
    import tools._http as http

    async def blocked(*args, **kwargs):
        raise AssertionError(
            f"network call attempted in test: {args[:1]}"
        )

    monkeypatch.setattr(http, "fetch_json", blocked, raising=False)
    monkeypatch.setattr(http, "fetch", blocked, raising=False)
    monkeypatch.setattr(http, "fetch_page", blocked, raising=False)
    monkeypatch.setattr(http, "fetch_text", blocked, raising=False)


@pytest.fixture
def result():
    """SearchResult factory for fixture evidence."""
    from datetime import timedelta

    from search.search_result import SearchResult
    from utils.time_utils import now_utc

    def make(
        *,
        title="A headline",
        content="Body text about the topic.",
        source="Example News",
        url="https://example.com/a",
        tool="brave",
        confidence=0.8,
        published=None,
    ):
        if published is None:
            published = (now_utc() - timedelta(hours=1)).isoformat()

        return SearchResult(
            title=title,
            content=content,
            source=source,
            url=url,
            tool=tool,
            confidence=confidence,
            published_at=published,
        )

    return make
