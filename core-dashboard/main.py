from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api.health import router as health_router
from app.api.api_connections import router as api_connections_router
from app.api.auth import router as auth_router
from app.api.finance import router as finance_router  # NOWY IMPORT
from database.db_setup import engine, Base  # ZMIENIONY IMPORT
import app.models  # NOWY IMPORT (rejestruje wszystkie modele)
from app.services.auth import get_current_user
import os

# Importy dla monitoringu SRE
from starlette_exporter import PrometheusMiddleware, handle_metrics

# Create directories if they don't exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Create database tables
# Ta jedna linia teraz stworzy WSZYSTKIE tabele (User, Health, ApiConnection, Transaction)
app.models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Health & Finance Dashboard",
              description="API to track health and financial data",
              version="0.1.0")

# --- SRE: Dodanie monitoringu Prometheus ---
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", handle_metrics)
# ------------------------------------------

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Add routers
app.include_router(health_router, prefix="/api/health", tags=["health"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(api_connections_router, prefix="/api", tags=["api_connections"])
app.include_router(finance_router, prefix="/api/finance", tags=["finance"])  # NOWY ROUTER

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Redirect to login page if not authenticated, otherwise to dashboard
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Display login page
    """
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Display registration page
    """
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def show_dashboard(request: Request):
    """
    Display health dashboard
    """
    return templates.TemplateResponse("health_dashboard.html", {"request": request})

@app.get("/connections", response_class=HTMLResponse)
async def connections_page(request: Request):
    """
    Display API connections management page
    """
    return templates.TemplateResponse("connections.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True) # Added reload for convenience