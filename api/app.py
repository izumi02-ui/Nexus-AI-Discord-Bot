"""
Project Nexus

Nexus API
"""

from fastapi import FastAPI

from api.routes.chat import router as chat_router
from api.routes.search import router as search_router
from api.routes.memory import router as memory_router
from api.routes.research import router as research_router
from api.routes.tools import router as tools_router
from api.routes.models import router as models_router
from api.routes.health import router as health_router


app = FastAPI(

    title="Nexus API",

    description="The core API powering Project Nexus.",

    version="2.0.0-alpha.1",

)


# ==========================================
# Routes
# ==========================================

app.include_router(

    health_router,

    prefix="/health",

    tags=["Health"],

)

app.include_router(

    chat_router,

    prefix="/chat",

    tags=["Chat"],

)

app.include_router(

    search_router,

    prefix="/search",

    tags=["Search"],

)

app.include_router(

    research_router,

    prefix="/research",

    tags=["Research"],

)

app.include_router(

    memory_router,

    prefix="/memory",

    tags=["Memory"],

)

app.include_router(

    tools_router,

    prefix="/tools",

    tags=["Tools"],

)

app.include_router(

    models_router,

    prefix="/models",

    tags=["Models"],

)


@app.get("/")

async def root():

    return {

        "name": "Nexus API",

        "version": "2.0.0-alpha.1",

        "status": "online",

    }
