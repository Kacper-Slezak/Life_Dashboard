# app/api/api_connections.py

from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session, relationship
from starlette.responses import RedirectResponse

from app.services.auth import get_current_user
from app.models.user import User
from app.models.api_connections import ApiConnection, ApiConnectionCreate, ApiConnectionResponse
from database.db_setup import get_db
from typing import  Dict, Any, List
import os
import dotenv
from datetime import datetime, timedelta
import secrets
from database.db_setup import Base
import requests

dotenv.load_dotenv()




# Router dla połączeń API
router = APIRouter(
    prefix="/api-connections",
    tags=["API Connections"],
    responses={404: {"description": "Not found"}}
)

@router.get("/", response_model=List[ApiConnectionResponse])
async def get_user_api_connections(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Pobiera listę wszystkich połączeń API dla zalogowanego użytkownika.
    """
    connections = db.query(ApiConnection).filter(
        ApiConnection.user_id == current_user.id
    ).all()

    return connections


@router.post("/", response_model=ApiConnectionResponse)
async def create_api_connection(
        connection_data: ApiConnectionCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Tworzy nowe połączenie API dla zalogowanego użytkownika.
    """
    # Sprawdzenie, czy połączenie z tym dostawcą już istnieje
    existing_connection = db.query(ApiConnection).filter(
        ApiConnection.user_id == current_user.id,
        ApiConnection.provider == connection_data.provider
    ).first()

    if existing_connection:
        # Aktualizacja istniejącego połączenia
        for key, value in connection_data.model_dump().items(): # Zmieniono .dict() na .model_dump()
            if value is not None:
                setattr(existing_connection, key, value)

        existing_connection.updated_at = datetime.now()
        existing_connection.is_active = True

        db.commit()
        db.refresh(existing_connection)
        return existing_connection

    # Utworzenie nowego połączenia
    new_connection = ApiConnection(
        user_id=current_user.id,
        **connection_data.model_dump() # Zmieniono .dict() na .model_dump()
    )

    db.add(new_connection)
    db.commit()
    db.refresh(new_connection)

    return new_connection


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_connection(
        connection_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Usuwa połączenie API dla zalogowanego użytkownika.
    """
    connection = db.query(ApiConnection).filter(
        ApiConnection.id == connection_id,
        ApiConnection.user_id == current_user.id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Połączenie API nie zostało znalezione"
        )

    db.delete(connection)
    db.commit()

    return None


# Fix the initialize_google_fit_auth function in api_connections.py

@router.post("/google-fit/auth", response_model=Dict[str, Any])
async def initialize_google_fit_auth(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Inicjalizuje proces autoryzacji z Google Fit.

    Generuje URL, na który użytkownik musi przejść, aby zalogować się do Google
    i udzielić zgody na dostęp do danych z Google Fit.
    """
    # Generowanie stanu dla zabezpieczenia CSRF
    state = secrets.token_urlsafe(16)

    # Zapisz stan w bazie danych dla późniejszej weryfikacji
    connection_data = {"auth_state": state}

    # Sprawdź, czy istnieje już połączenie z Google Fit dla tego użytkownika
    existing_connection = db.query(ApiConnection).filter(
        ApiConnection.user_id == current_user.id,
        ApiConnection.provider == "google_fit"
    ).first()

    if existing_connection:
        # Aktualizacja istniejącego połączenia
        existing_connection.connection_data = connection_data
        existing_connection.updated_at = datetime.now()
        db.commit()
    else:
        # Utworzenie nowego połączenia (jeszcze bez tokenów)
        new_connection = ApiConnection(
            user_id=current_user.id,
            provider="google_fit",
            connection_data=connection_data
        )
        db.add(new_connection)
        db.commit()

    # Adres zwrotny, na który Google przekieruje użytkownika po autoryzacji
    # Construct the redirect URI manually instead of using url_for
    base_url = os.getenv('APP_BASE_URL', 'http://localhost:8080')
    redirect_uri = f"{base_url}/api/api-connections/google-fit/callback"

    # Zakres uprawnień dla Google Fit
    scopes = [
        "https://www.googleapis.com/auth/fitness.activity.read",
        "https://www.googleapis.com/auth/fitness.sleep.read",
        "https://www.googleapis.com/auth/fitness.heart_rate.read",
        "https://www.googleapis.com/auth/fitness.body.read",
        "https://www.googleapis.com/auth/fitness.location.read"
    ]

    # Sprawdzenie czy GOOGLE_CLIENT_ID jest dostępny
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Brak konfiguracji GOOGLE_CLIENT_ID. Skontaktuj się z administratorem."
        )

    # URL autoryzacji Google
    ...
    auth_url = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={'%20'.join(scopes)}&state={state}&access_type=offline&prompt=consent"

    # DODAJ TEN PRINT
    print(f"DEBUG: URL Autoryzacji: {auth_url}")
    print(f"DEBUG: Redirect URI (Init): {redirect_uri}")
    

    return {
        "auth_url": auth_url,
        "state": state,
        "message": "Przejdź na podany URL, aby zalogować się do Google Fit"
    }

# Update the callback route in api_connections.py to include a name

@router.get("/google-fit/callback", name="google_fit_callback")
async def google_fit_callback(
        code: str,
        state: str,
        db: Session = Depends(get_db)
):
    """
    Obsługuje callback od Google po autoryzacji.

    Wymienia kod autoryzacyjny na tokeny dostępu i odświeżania.
    """
    # Znajdź połączenie z tym stanem dla weryfikacji CSRF
    connection = db.query(ApiConnection).filter(
        ApiConnection.provider == "google_fit",
        ApiConnection.connection_data.op('->>')('auth_state') == state
    ).first()

    if not connection:
        return RedirectResponse(url="/connections?auth_success=false")

    # Adres API Google do wymiany kodu
    token_url = "https://oauth2.googleapis.com/token"

    # Odbierz CLIENT_ID i CLIENT_SECRET z zmiennych środowiskowych
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

    if not client_id or not client_secret:
        return RedirectResponse(url="/connections?auth_success=false")

    # Pełny URL do callbacku
    base_url = os.getenv('APP_BASE_URL', 'http://localhost:8080')
    redirect_uri = f"{base_url}/api/api-connections/google-fit/callback"

    # DODAJ TEN PRINT
    print(f"DEBUG: Redirect URI (Callback): {redirect_uri}")
    print(f"DEBUG: Otrzymany 'code': {code}")
    print(f"DEBUG: Otrzymany 'state': {state}")
    # Parametry żądania wymiany kodu na tokeny
    token_params = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }

    try:
        # Wykonanie żądania HTTP do Google API
        response = requests.post(token_url, data=token_params)
        response.raise_for_status()  # Sprawdzenie czy nie ma błędu HTTP

        token_data = response.json()

        # Pobierz tokeny z odpowiedzi
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        if not access_token:
            return RedirectResponse(url="/connections?auth_success=false")

        # Oblicz datę wygaśnięcia tokenu
        token_expires_at = datetime.now() + timedelta(seconds=expires_in) if expires_in else None

        # Aktualizuj połączenie w bazie danych
        connection.access_token = access_token
        connection.refresh_token = refresh_token
        connection.token_expires_at = token_expires_at
        connection.is_active = True
        connection.updated_at = datetime.now()

        db.commit()

        # Przekieruj użytkownika z powrotem do strony połączeń z informacją o sukcesie
        return RedirectResponse(url="/connections?auth_success=true")

    except requests.RequestException as e:
        print(f"Google API error: {str(e)}")
        return RedirectResponse(url="/connections?auth_success=false")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return RedirectResponse(url="/connections?auth_success=false")