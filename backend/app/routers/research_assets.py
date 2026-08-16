from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..models import ResearchMethod, ResearchTool, ResearchWorkflow, User, now
from ..schemas import (
    OkResponse,
    ResearchMethodCreate,
    ResearchMethodResponse,
    ResearchToolCreate,
    ResearchToolResponse,
    ResearchWorkflowCreate,
    ResearchWorkflowResponse,
)

router = APIRouter(prefix="/research-assets", tags=["research-assets"])


@router.get("/methods", response_model=list[ResearchMethodResponse])
def list_methods(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(ResearchMethod).order_by(ResearchMethod.updated_at.desc()).limit(500).all()


@router.post("/methods", response_model=ResearchMethodResponse)
def create_method(
    payload: ResearchMethodCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = ResearchMethod(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/methods/{asset_id}", response_model=ResearchMethodResponse)
def update_method(
    asset_id: int,
    payload: ResearchMethodCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.get(ResearchMethod, asset_id)
    if not item:
        raise HTTPException(status_code=404, detail="Research method not found")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    item.updated_at = now()
    db.commit()
    db.refresh(item)
    return item


@router.delete("/methods/{asset_id}", response_model=OkResponse)
def delete_method(asset_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.get(ResearchMethod, asset_id)
    if not item:
        raise HTTPException(status_code=404, detail="Research method not found")
    db.delete(item)
    db.commit()
    return OkResponse()


@router.get("/tools", response_model=list[ResearchToolResponse])
def list_tools(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(ResearchTool).order_by(ResearchTool.updated_at.desc()).limit(500).all()


@router.post("/tools", response_model=ResearchToolResponse)
def create_tool(
    payload: ResearchToolCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = ResearchTool(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/tools/{asset_id}", response_model=ResearchToolResponse)
def update_tool(
    asset_id: int,
    payload: ResearchToolCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.get(ResearchTool, asset_id)
    if not item:
        raise HTTPException(status_code=404, detail="Research tool not found")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    item.updated_at = now()
    db.commit()
    db.refresh(item)
    return item


@router.delete("/tools/{asset_id}", response_model=OkResponse)
def delete_tool(asset_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.get(ResearchTool, asset_id)
    if not item:
        raise HTTPException(status_code=404, detail="Research tool not found")
    db.delete(item)
    db.commit()
    return OkResponse()


@router.get("/workflows", response_model=list[ResearchWorkflowResponse])
def list_workflows(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(ResearchWorkflow).order_by(ResearchWorkflow.updated_at.desc()).limit(500).all()


@router.post("/workflows", response_model=ResearchWorkflowResponse)
def create_workflow(
    payload: ResearchWorkflowCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = ResearchWorkflow(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/workflows/{asset_id}", response_model=ResearchWorkflowResponse)
def update_workflow(
    asset_id: int,
    payload: ResearchWorkflowCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.get(ResearchWorkflow, asset_id)
    if not item:
        raise HTTPException(status_code=404, detail="Research workflow not found")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    item.updated_at = now()
    db.commit()
    db.refresh(item)
    return item


@router.delete("/workflows/{asset_id}", response_model=OkResponse)
def delete_workflow(asset_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.get(ResearchWorkflow, asset_id)
    if not item:
        raise HTTPException(status_code=404, detail="Research workflow not found")
    db.delete(item)
    db.commit()
    return OkResponse()
