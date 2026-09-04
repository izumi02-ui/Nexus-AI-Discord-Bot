"""
Project Nexus

Model Catalog

Nexus' second meaning of "update itself": it re-reads what its providers
actually offer and repairs its own configuration when a model id disappears.

Free-tier providers rename and retire models constantly - the moment one of
the ids in OPENROUTER_MODELS is gone, every message falls through to the last
provider in the chain. Instead of waiting for that to be noticed, the
self-updater asks each provider for its live catalog, keeps a snapshot, and
swaps a retired model for the closest working one.
"""

import json
from pathlib import Path

from tools._http import FetchError, fetch_json
from utils.logger import logger
from utils.settings import settings
from utils.time_utils import iso, now_utc

CATALOG_PATH = Path("data/model_catalog.json")

STATE_KEY = "model_catalog_at"

#: OpenAI-compatible list endpoints. Ollama has its own shape, handled below.
ENDPOINTS = {
    "openrouter": (
        "https://openrouter.ai/api/v1/models",
        lambda key: {"Authorization": f"Bearer {key}"},
    ),
    "groq": (
        "https://api.groq.com/openai/v1/models",
        lambda key: {"Authorization": f"Bearer {key}"},
    ),
    "openai": (
        "https://api.openai.com/v1/models",
        lambda key: {"Authorization": f"Bearer {key}"},
    ),
    "deepseek": (
        "https://api.deepseek.com/models",
        lambda key: {"Authorization": f"Bearer {key}"},
    ),
    "mistral": (
        "https://api.mistral.ai/v1/models",
        lambda key: {"Authorization": f"Bearer {key}"},
    ),
}


def _free(model: dict) -> bool:
    pricing = model.get("pricing") or {}

    try:
        return all(
            float(value or 0) == 0.0
            for value in (pricing.get("prompt"), pricing.get("completion"))
        ) or str(model.get("id", "")).endswith(":free")
    except (TypeError, ValueError):
        return False


def _context(model: dict) -> int:
    for key in ("context_length", "max_context_window", "supported_input_tokens"):
        value = model.get(key)

        if isinstance(value, (int, float)):
            return int(value)

    return 0


def _quality_score(model: dict) -> float:
    """
    Rank candidates so a swap never downgrades to something tiny.

    Context length dominates (long context keeps memory + evidence intact),
    free-ness breaks ties, since the bot must run on a zero budget by default.
    """
    return _context(model) + (400_000 if _free(model) else 0)


async def list_models(provider_key: str) -> list[dict]:
    """
    Live model list for a provider, normalised to [{'id', 'context', 'free'}].
    """
    if provider_key == "ollama":
        try:
            data = await fetch_json(
                f"{settings.ollama_url.rstrip('/')}/api/tags", timeout=6
            )

            return [
                {"id": model.get("name"), "context": 0, "free": True}
                for model in (data or {}).get("models", [])
                if model.get("name")
            ]
        except Exception as error:  # noqa: BLE001 - local server may be off
            logger.debug("Ollama catalog unavailable: %s", error)

            return []

    entry = ENDPOINTS.get(provider_key)

    if not entry:
        return []

    url, header_factory = entry

    key = {
        "openrouter": settings.openrouter_api_key,
        "mistral": settings.mistral_api_key,
        "groq": settings.groq_api_key,
        "openai": settings.openai_api_key,
        "deepseek": settings.deepseek_api_key,
    }.get(provider_key)

    if not key:
        return []

    try:
        data = await fetch_json(
            url,
            headers=header_factory(key),
            timeout=15,
        )
    except FetchError as error:
        logger.warning("%s model catalog unavailable: %s", provider_key, error)

        return []

    if isinstance(data, list):
        # Some providers (Mistral) return a bare array instead of {"data": []}.
        rows = data
    else:
        rows = (data or {}).get("data") or (data or {}).get("models") or []

    models = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        model_id = row.get("id") or row.get("name")

        if not model_id:
            continue

        models.append(
            {
                "id": model_id,
                "name": row.get("name") or model_id,
                "context": _context(row),
                "free": _free(row),
                "created": row.get("created"),
            }
        )

    return models


def _load_snapshot() -> dict:
    if not CATALOG_PATH.exists():
        return {}

    try:
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _save_snapshot(payload: dict):
    try:
        CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        CATALOG_PATH.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError as error:  # pragma: no cover - read-only filesystem
        logger.warning("Could not write model catalog: %s", error)


async def refresh(*, provider=None) -> dict:
    """
    Pull the catalogs and repair configured model ids.

    Returns a summary of what was found and what was changed; nothing is
    changed when the live list cannot be fetched, so a network blip can never
    leave the bot without a model.
    """
    keys = [provider] if provider else list(ENDPOINTS) + ["ollama"]

    summary = {
        "checked": [],
        "changed": [],
        "unavailable": [],
        "at": iso(now_utc()),
        "catalog": {},
    }

    snapshot = _load_snapshot()

    for key in keys:
        models = await list_models(key)

        if not models:
            summary["unavailable"].append(key)

            continue

        ids = {model["id"] for model in models}

        summary["checked"].append(key)

        summary["catalog"][key] = {
            "count": len(models),
            "free": sum(1 for model in models if model["free"]),
            "largest_context": max((_context(model) for model in models), default=0),
        }

        snapshot[key] = {
            "at": summary["at"],
            "models": [model["id"] for model in models][:2000],
        }

        if key == "openrouter":
            changed = await _repair_openrouter(ids, models)

            if changed:
                summary["changed"].append(changed)
        elif key in {"groq", "openai", "deepseek", "mistral"}:
            changed = await _repair_single(key, ids, models)

            if changed:
                summary["changed"].append(changed)

    _save_snapshot(snapshot)

    try:
        from database.database import database

        database.set_state(STATE_KEY, summary["at"])
    except Exception:  # noqa: BLE001 - snapshot file is enough
        pass

    if summary["changed"]:
        logger.info(
            "Model catalog refresh repaired %s provider(s).",
            len(summary["changed"]),
        )

    return summary


async def _repair_openrouter(ids: set[str], models: list[dict]) -> dict | None:
    from ai.provider_manager import provider_manager

    provider = provider_manager.providers.get("openrouter")

    if provider is None:
        return None

    configured = list(getattr(provider, "models", []))

    missing = [model for model in configured if model not in ids]

    if not missing:
        return None

    by_id = {model["id"]: model for model in models}

    replacements = []

    for dead in missing:
        base = dead.split(":")[0]

        candidates = [
            candidate["id"]
            for candidate in models
            if candidate["id"] != dead
            and candidate["id"] not in configured
            and (candidate["id"].split(":")[0] == base or _free(candidate))
        ]

        candidates.sort(
            key=lambda candidate_id: -_quality_score(by_id[candidate_id])
        )

        if candidates:
            replacements.append({"was": dead, "now": candidates[0]})
        else:
            replacements.append({"was": dead, "now": None})

    kept = [model for model in configured if model in ids]

    added = [
        item["now"]
        for item in replacements
        if item["now"] and item["now"] not in kept
    ]

    chain = kept + added

    if not chain:
        logger.warning(
            "No configured OpenRouter models exist any more and no replacement "
            "was found; leaving the chain untouched."
        )

        return None

    provider.set_models(chain)

    settings.openrouter_models = chain

    return {
        "provider": "openrouter",
        "missing": missing,
        "chain": chain,
        "replacements": replacements,
    }


async def _repair_single(
    key: str,
    ids: set[str],
    models: list[dict],
) -> dict | None:
    from ai.provider_manager import provider_manager

    provider = provider_manager.providers.get(key)

    if provider is None:
        return None

    current = provider.model

    if current in ids:
        return None

    setting = f"{key}_model"

    if not hasattr(settings, setting):
        return {"provider": key, "missing": [current], "now": None}

    base = current.split(":")[0].split("@")[0]

    ranked = sorted(
        (model for model in models if model["id"] != current),
        key=lambda model: (
            -(400_000 if _free(model) else 0) - _context(model),
            0 if base and base in model["id"] else 1,
            model["id"],
        ),
    )

    if not ranked:
        logger.warning(
            "%s no longer serves %r and offers nothing else; leaving it alone.",
            key,
            current,
        )

        return {"provider": key, "missing": [current], "now": None}

    replacement = ranked[0]["id"]

    # The runtime override only: config.py stays authoritative for the next
    # restart, so a temporary provider-side rename cannot silently persist.
    setattr(settings, setting, replacement)

    logger.warning(
        "%s no longer serves %r - using %r for this session.",
        key,
        current,
        replacement,
    )

    return {
        "provider": key,
        "missing": [current],
        "now": replacement,
        "replacements": [{"was": current, "now": replacement}],
    }


def status() -> dict:
    """What the last refresh saw, for /status and the API."""
    snapshot = _load_snapshot()

    return {
        "providers": {
            key: {
                "count": len(value.get("models", [])),
                "refreshed_at": value.get("at"),
            }
            for key, value in snapshot.items()
            if isinstance(value, dict)
        },
        "configured": {
            "openrouter": list(settings.openrouter_models),
            "gemini": settings.gemini_model,
            "openai": settings.openai_model,
            "groq": settings.groq_model,
            "deepseek": settings.deepseek_model,
            "mistral": settings.mistral_model,
            "cohere": settings.cohere_model,
            "ollama": settings.ollama_model,
        },
    }
