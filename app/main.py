from app.database import check_database_connection

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserRegister, UserResponse, UserLogin
from app.security import hash_password, verify_password

from fastapi.security import OAuth2PasswordRequestForm
from app.auth import create_access_token
from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
)


from app.auth import get_current_user, get_admin_user
from app.models import User
from app.schemas import UserResponse

from app.admin import router as admin_router

from app.posts import router as posts_router

from app.comments import router as comments_router

app = FastAPI(
    title="Social Media API",
    description="Social media backend using FastAPI and PostgreSQL",
    version="1.0.0",
)

app.include_router(admin_router)

app.include_router(posts_router)

app.include_router(comments_router)

@app.get("/")
def home():
    return {"message": "Social Media API is running"}


@app.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    try:
        database_name = check_database_connection()

        return {
            "status": "connected",
            "database": database_name,
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )


@app.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    existing_user = db.query(User).filter(
        (User.username == user_data.username)
        | (User.email == user_data.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    new_user = User(
        username=user_data.username,
        email=str(user_data.email),
        password_hash=hash_password(user_data.password),
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )




@app.post("/auth/login")
def login_user(
    login_data: UserLogin,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.email == str(login_data.email)
    ).first()

    if user is None or not verify_password(
        login_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_blocked:
        raise HTTPException(
            status_code=403,
            detail="Your account has been blocked",
        )

    access_token = create_access_token(str(user.id))

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@app.get("/auth/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


@app.get("/admin/check")
def admin_check(
    admin_user: User = Depends(get_admin_user),
):
    return {
        "message": "Admin access granted",
        "username": admin_user.username,
        "role": admin_user.role,
    }
