"""Central API router.

Feature routers (terms, concepts, review queue, ...) get registered here as
they land.
"""

from fastapi import APIRouter

from app.api.routes import auth, setup, users

api_router = APIRouter()
api_router.include_router(setup.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
