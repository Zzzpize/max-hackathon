from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_teacher
from app.db import get_session
from app.modules.dashboard.aggregate import class_summary
from app.schemas.student import ClassDashboardOut

router = APIRouter(prefix="/classes", tags=["stats"])


@router.get("/{class_id}/dashboard", response_model=ClassDashboardOut)
async def class_dashboard(
    class_id: str,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> ClassDashboardOut:
    return await class_summary(class_id, teacher_id, session)
