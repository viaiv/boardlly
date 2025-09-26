from fastapi import APIRouter

from app.api.routers import accounts, auth, users, settings, github, projects

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(auth.router)
api_router.include_router(accounts.router)
api_router.include_router(settings.router)
api_router.include_router(github.router)
api_router.include_router(projects.router)
api_router.include_router(users.router)
