"""Task CRUD — ownership-enforced, paginated reads."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import Task, User
from app.schemas import Page, TaskIn, TaskOut, TaskPatch

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=Page)
async def list_tasks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    task_status: str | None = Query(None, pattern="^(todo|doing|done)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page:
    base = select(Task).where(Task.owner_id == user.id)
    if task_status:
        base = base.where(Task.status == task_status)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = (await db.scalars(base.order_by(Task.created_at.desc())
                             .offset((page - 1) * size).limit(size))).all()
    return Page(items=rows, total=total, page=page, size=size)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskIn, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)) -> Task:
    task = Task(owner_id=user.id, **payload.model_dump())
    db.add(task)
    await db.flush()
    return task


async def _owned_task(task_id: int, user: User, db: AsyncSession) -> Task:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if task.owner_id != user.id and user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your task")
    return task


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, user: User = Depends(get_current_user),
                   db: AsyncSession = Depends(get_db)) -> Task:
    return await _owned_task(task_id, user, db)


@router.patch("/{task_id}", response_model=TaskOut)
async def patch_task(task_id: int, payload: TaskPatch,
                     user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)) -> Task:
    task = await _owned_task(task_id, user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.flush()
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)) -> None:
    task = await _owned_task(task_id, user, db)
    await db.delete(task)
