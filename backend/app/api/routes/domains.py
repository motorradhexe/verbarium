"""Domains — the subject fields a concept can be filed under. → D9"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession, require_role
from app.models.enums import Role
from app.schemas.concept import DomainCreate, DomainRead
from app.services import concepts as concept_service

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("", response_model=list[DomainRead], summary="List domains")
def list_domains(db: DbSession) -> list[DomainRead]:
    return concept_service.list_domains(db)


@router.post(
    "",
    response_model=DomainRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a domain",
    dependencies=[Depends(require_role(Role.EDITOR))],
)
def create_domain(request: DomainCreate, db: DbSession) -> DomainRead:
    try:
        return concept_service.create_domain(db, request.name)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A domain with this name already exists",
        ) from None
