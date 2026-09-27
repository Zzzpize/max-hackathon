from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.student import ClassDashboardOut

router = APIRouter(prefix="/classes", tags=["stats"])


@router.get("/{class_id}/dashboard", response_model=ClassDashboardOut)
async def class_dashboard(
    class_id: str,
    session: AsyncSession = Depends(get_session),
) -> ClassDashboardOut:
    # TODO(backend, dashboard module): агрегация профилей учеников класса
    return ClassDashboardOut(
        class_id=class_id,
        students_count=0,
        avg_score=0.0,
    )
