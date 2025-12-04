# app/api/api_connections.py

from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.services.auth import get_current_user
from app.models.user import User
from app.models.api_connections import ApiConnection, ApiConnectionCreate, ApiConnectionResponse
from database.db_setup import get_db
from typing import Dict, Any, List
import os
import dotenv
from datetime import datetime, timedelta
import secrets
import requests

dotenv.load_dotenv()


# Router for API connections
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
    Return a list of all API connections for the authenticated user.
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
    Create or update an API connection for the authenticated user.
    """
    # Check if connection with this provider already exists
    existing_connection = db.query(ApiConnection).filter(
        ApiConnection.user_id == current_user.id,
        ApiConnection.provider == connection_data.provider
    ).first()

    if existing_connection:
        # Update existing connection
        for key, value in connection_data.model_dump().items(): # Changed .dict() to .model_dump()
            if value is not None:
                setattr(existing_connection, key, value)

        existing_connection.updated_at = datetime.now()
        existing_connection.is_active = True

        db.commit()
        db.refresh(existing_connection)
        return existing_connection

    # Create new connection
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
    Delete API connection for the authenticated user.
    """
    connection = db.query(ApiConnection).filter(
        ApiConnection.id == connection_id,
        ApiConnection.user_id == current_user.id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API connection not found"
        )

    db.delete(connection)
    db.commit()

    return None


@router.post("/google-fit/auth", response_model=Dict[str, Any])
async def initialize_google_fit_auth(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Initialize Google Fit authorization.

    Generates the URL the user must visit to sign in with Google and grant
    access to Google Fit data.
    """
    # Generowanie stanu dla zabezpieczenia CSRF
    state = secrets.token_urlsafe(16)

    # Save state in database for later verification
    connection_data = {"auth_state": state}

    # Check if Google Fit connection already exists for this user
    existing_connection = db.query(ApiConnection).filter(
        ApiConnection.user_id == current_user.id,
        ApiConnection.provider == "google_fit"
    ).first()

    if existing_connection:
        # Update existing connection
        existing_connection.connection_data = connection_data
        existing_connection.updated_at = datetime.now()
        db.commit()
    else:
        # Create new connection (without tokens yet)
        new_connection = ApiConnection(
            user_id=current_user.id,
            provider="google_fit",
            connection_data=connection_data
        )
        db.add(new_connection)
        db.commit()

    # Adres zwrotny, na który Google przekieruje użytkownika po autoryzacji
    # FIX: Changed default port from 8080 to 8000, which is the container's exposed port.
    base_url = os.getenv('APP_BASE_URL', 'http://localhost:8000') 
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
            detail="GOOGLE_CLIENT_ID not configured. Contact the administrator."
        )

    # URL autoryzacji Google
    auth_url = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={'%20'.join(scopes)}&state={state}&access_type=offline&prompt=consent"

    # Debug prints
    print(f"DEBUG: Authorization URL: {auth_url}")
    print(f"DEBUG: Redirect URI (Init): {redirect_uri}")
    

    return {
        "auth_url": auth_url,
        "state": state,
        "message": "Open the provided URL to sign in to Google Fit"
    }


@router.get("/google-fit/callback", name="google_fit_callback")
async def google_fit_callback(
        code: str,
        state: str,
        db: Session = Depends(get_db)
):
    """
    Handle Google callback after authorization.

    Exchanges the authorization code for access and refresh tokens.
    """
    # Find connection with this state for CSRF verification
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
    # FIX: Changed default port from 8080 to 8000, which is the container's exposed port.
    base_url = os.getenv('APP_BASE_URL', 'http://localhost:8000') 
    redirect_uri = f"{base_url}/api/api-connections/google-fit/callback"

    # Debug prints
    print(f"DEBUG: Redirect URI (Callback): {redirect_uri}")
    print(f"DEBUG: Received 'code': {code}")
    print(f"DEBUG: Received 'state': {state}")
    # Token exchange request parameters
    token_params = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }

    try:
        # Execute HTTP request to Google API
        response = requests.post(token_url, data=token_params)
        response.raise_for_status()

        token_data = response.json()

        # Get tokens from response
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        if not access_token:
            return RedirectResponse(url="/connections?auth_success=false")

        # Compute token expiration time
        token_expires_at = datetime.now() + timedelta(seconds=expires_in) if expires_in else None

        # Update connection in database
        connection.access_token = access_token
        connection.refresh_token = refresh_token
        connection.token_expires_at = token_expires_at
        connection.is_active = True
        connection.updated_at = datetime.now()

        db.commit()

        # Redirect user back to connections page with success information
        return RedirectResponse(url="/connections?auth_success=true")

    except requests.RequestException as e:
        print(f"Google API error: {str(e)}")
        return RedirectResponse(url="/connections?auth_success=false")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return RedirectResponse(url="/connections?auth_success=false")