"""Central API router.

Feature routers (terms, concepts, review queue, ...) get registered here as
they land.
"""

from fastapi import APIRouter

from app.api.routes import auth, concepts, domains, setup, terms, users

api_router = APIRouter()
api_router.include_router(setup.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(domains.router)
api_router.include_router(concepts.router)
api_router.include_router(terms.router)
