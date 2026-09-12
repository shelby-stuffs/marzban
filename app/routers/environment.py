import os
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from app.env_manager import read_environment,update_environment
from app.models.admin import Admin
ENV_FILE_PATH=os.getenv("ENV_FILE_PATH","/var/lib/marzban/.env")
router=APIRouter(prefix="/api/environment",tags=["Environment"])
class EnvironmentChange(BaseModel):
 key:str
 value:str|None=None
 delete:bool=False
class EnvironmentUpdate(BaseModel):
 changes:list[EnvironmentChange]=Field(default_factory=list,max_length=200)
@router.get("")
def get_environment(_admin:Admin=Depends(Admin.check_sudo_admin)):
 try:return read_environment(ENV_FILE_PATH)
 except (OSError,ValueError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
@router.put("")
def put_environment(payload:EnvironmentUpdate,_admin:Admin=Depends(Admin.check_sudo_admin)):
 try:
  result=update_environment(ENV_FILE_PATH,[item.model_dump() for item in payload.changes]);result["restart_required"]=True;return result
 except (OSError,ValueError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
