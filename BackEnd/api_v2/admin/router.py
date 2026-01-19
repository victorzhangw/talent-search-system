
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from .auth import create_access_token, get_password_hash, verify_password, get_db, verify_token
from ..database.models import AdminUser

router = APIRouter(prefix="/api/admin", tags=["admin"])

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class AdminCreate(BaseModel):
    username: str
    password: str

@router.post("/login", response_model=Token)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.username == request.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def read_users_me(current_user: str = Depends(verify_token)):
    return {"username": current_user}

# Utility: Create initial admin (protected or run manually)
# For now, let's allow creating one if none exist? Or just a script?
# Let's keep it simple: Script preferred. But for dev demo:
@router.post("/register-dev") # REMOVE IN PROD
async def register(request: AdminCreate, db: Session = Depends(get_db)):
    # Check if any admin exists
    if db.query(AdminUser).count() > 0:
         raise HTTPException(status_code=400, detail="Admins already exist.")
         
    hashed_password = get_password_hash(request.password)
    new_user = AdminUser(username=request.username, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"username": new_user.username}
