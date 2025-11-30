from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.services.auth import get_current_user
from app.models.user import User
from app.models.transaction import Transaction , TransactionCreate, TransactionResponse
from database.db_setup import get_db


router = APIRouter()




@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Tworzy nową transakcję finansową dla zalogowanego użytkownika.
    """
    new_transaction = Transaction(
        **transaction_data.model_dump(),
        user_id=current_user.id
    )
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)
    return new_transaction


@router.get("/", response_model=List[TransactionResponse])
async def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pobiera listę wszystkich transakcji finansowych zalogowanego użytkownika.
    """
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.date.desc()).all()
    
    return transactions