from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models import User, Vehicle
from backend.app.security import hash_password, verify_password, create_access_token
from backend.app.dependencies import get_current_user
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str = ""
    license_plate: str = ""
    make_model: str = ""
    color: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str
    full_name: str


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        phone=body.phone,
        role="user",
    )
    db.add(user)
    db.flush()

    if body.license_plate:
        vehicle = Vehicle(
            user_id=user.id,
            license_plate=body.license_plate,
            make_model=body.make_model,
            color=body.color,
        )
        db.add(vehicle)

    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.role)
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.id, user.role)
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
    )


@router.post("/logout")
def logout():
    return {"message": "Logged out"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "role": current_user.role,
        "created_at": current_user.created_at,
    }


@router.get("/me/vehicles")
def my_vehicles(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vehicles = db.query(Vehicle).filter(Vehicle.user_id == current_user.id).all()
    return [
        {
            "id": v.id,
            "user_id": v.user_id,
            "license_plate": v.license_plate,
            "make_model": v.make_model,
            "color": v.color,
        }
        for v in vehicles
    ]


@router.post("/me/vehicles", status_code=201)
def add_vehicle(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    v = Vehicle(
        user_id=current_user.id,
        license_plate=body.get("license_plate", ""),
        make_model=body.get("make_model"),
        color=body.get("color"),
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return {"id": v.id, "license_plate": v.license_plate, "make_model": v.make_model, "color": v.color}
