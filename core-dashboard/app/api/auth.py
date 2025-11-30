from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from app.services.auth import create_access_token, get_current_user, verify_password, get_password_hash
from database.db_setup import get_db
from sqlalchemy.orm import Session
from app.models.user import User, UserRegister, UserResponse, TokenData


router = APIRouter(tags=["Auth"])




@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.

    Checks whether a user with the provided username or email already exists,
    verifies passwords match, and creates a new user account.
    """
    # Check that passwords match
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    # Check whether the user already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()

    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this username already exists"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )

    # Utworzenie nowego użytkownika
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=TokenData)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticate user and generate JWT token.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check whether the account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generowanie tokenu JWT
    access_token = create_access_token({"sub": user.username})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Handle logout request from the frontend.

    For JWTs, the server does not need to take action because the client
    (browser) removes the token. Token blacklist logic could be implemented here.
    """
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """
    Retrieve the currently authenticated user's profile.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
        user_data: dict = Body(...),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Update the currently authenticated user's profile.
    """
    # Update user data
    for key, value in user_data.items():
        if key == "password":
            # If password change, hash it
            setattr(current_user, "hashed_password", get_password_hash(value))
        elif key != "hashed_password" and hasattr(current_user, key):
            # Update other fields (except direct password hash setting)
            setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)

    return current_user