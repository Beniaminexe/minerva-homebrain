import asyncio

from fastapi import FastAPI

from .api.routes_status import router as status_router
from .api.routes_assistant import router as assistant_router
from .api.routes_reminders import router as reminders_router
from .api.routes_occurrences import router as occurrences_router
from .core.database import Base, engine, SessionLocal
from .core.seed import seed_initial_data
from .core.reminder_engine import occurrence_scheduler_loop
from .core.service_checker import service_checker_loop
from .api.routes_services import router as services_router
from .api.routes_words import router as words_router




app = FastAPI(
    title="Minerva Home Brain",
    version="0.1.0",
)


@app.on_event("startup")
async def startup_event():
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Seed if empty
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()

    # Start reminder scheduler
    asyncio.create_task(occurrence_scheduler_loop())

    # Start service checker
    asyncio.create_task(service_checker_loop())



app.include_router(status_router)
app.include_router(assistant_router)
app.include_router(reminders_router)
app.include_router(occurrences_router)
app.include_router(services_router)
app.include_router(words_router)
