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
    Rejestracja nowego użytkownika w systemie.

    Sprawdza, czy użytkownik o podanej nazwie lub emailu już istnieje,
    weryfikuje zgodność haseł i tworzy nowe konto użytkownika.
    """
    # Sprawdzenie czy hasła są zgodne
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hasła nie są zgodne"
        )

    # Sprawdzenie czy użytkownik już istnieje
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()

    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Użytkownik o tej nazwie już istnieje"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Użytkownik o tym adresie email już istnieje"
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
    Logowanie użytkownika i generowanie tokenu JWT.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Niepoprawna nazwa użytkownika lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Sprawdzenie czy konto jest aktywne
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Konto jest nieaktywne",
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
    Obsługuje żądanie wylogowania z frontendu.
    W przypadku JWT, serwer nie musi nic robić, 
    ponieważ klient (przeglądarka) usuwa token.
    Można tu zaimplementować logikę blacklisty tokenów.
    """
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """
    Pobiera profil aktualnie zalogowanego użytkownika.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
        user_data: dict = Body(...),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Aktualizuje profil aktualnie zalogowanego użytkownika.
    """
    # Aktualizacja danych użytkownika
    for key, value in user_data.items():
        if key == "password":
            # Jeśli zmiana hasła, należy je zahaszować
            setattr(current_user, "hashed_password", get_password_hash(value))
        elif key != "hashed_password" and hasattr(current_user, key):
            # Aktualizacja innych pól (z wyjątkiem bezpośredniego ustawiania hasza hasła)
            setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)

    return current_user