from fastapi import APIRouter
from .routes.auth import router as auth_router
from .routes.courses import router as courses_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(courses_router)
