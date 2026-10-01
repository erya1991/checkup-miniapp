"""Profile-scoped metric views and preferences."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import profile_metrics as service
from app.api.v1.confirmation import transaction
from app.core.auth import current_user, db_session
from app.models import User

router = APIRouter()
DB_DEP = Depends(db_session)
USER_DEP = Depends(current_user)


@router.get("/profile-metrics")
def metrics(health_profile_id: str, page: int = Query(1, ge=1),
            page_size: int = Query(20, ge=1, le=100),
            user: User = USER_DEP, db: Session = DB_DEP):
    return service.list_metrics(db, user, health_profile_id, page, page_size)


@router.get("/profile-metrics/{standard_metric_id}")
def detail(standard_metric_id: str, health_profile_id: str,
           user: User = USER_DEP, db: Session = DB_DEP):
    return service.detail(db, user, health_profile_id, standard_metric_id)


@router.get("/profile-metrics/{standard_metric_id}/history")
def history(standard_metric_id: str, health_profile_id: str, page: int = Query(1, ge=1),
            page_size: int = Query(50, ge=1, le=100),
            user: User = USER_DEP, db: Session = DB_DEP):
    return service.history(db, user, health_profile_id, standard_metric_id, page, page_size)


@router.get("/profile-metrics/{standard_metric_id}/trend")
def trend(standard_metric_id: str, health_profile_id: str,
          user: User = USER_DEP, db: Session = DB_DEP):
    return service.trend(db, user, health_profile_id, standard_metric_id)


@router.put("/favorites/{standard_metric_id}")
def favorite(standard_metric_id: str, health_profile_id: str,
             user: User = USER_DEP, db: Session = DB_DEP):
    with transaction(db):
        result = service.set_favorite(db, user, health_profile_id, standard_metric_id, True)
    return result


@router.delete("/favorites/{standard_metric_id}")
def unfavorite(standard_metric_id: str, health_profile_id: str,
               user: User = USER_DEP, db: Session = DB_DEP):
    with transaction(db):
        result = service.set_favorite(db, user, health_profile_id, standard_metric_id, False)
    return result
