from fastapi import FastAPI
from .api.routes_status import router as status_router
from .api.routes_assistant import router as assistant_router
from .core.database import Base, engine

Base.metadata.create_all(bind=engine)



app = FastAPI(
    title="Minerva Home Brain",
    version="0.1.0",
)


# Include routers
app.include_router(status_router)
app.include_router(assistant_router)
