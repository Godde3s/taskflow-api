"""Admin-only endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_admin
from app.models import Task, User
from app.schemas import StatsOut

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/stats", response_model=StatsOut)
async def stats(db: AsyncSession = Depends(get_db)) -> StatsOut:
    users = await db.scalar(select(func.count()).select_from(User)) or 0
    tasks = await db.scalar(select(func.count()).select_from(Task)) or 0
    done = await db.scalar(select(func.count()).select_from(Task).where(Task.status == "done")) or 0
    return StatsOut(users=users, tasks=tasks, tasks_done=done)
