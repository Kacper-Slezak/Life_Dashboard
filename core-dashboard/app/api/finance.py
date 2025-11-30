from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from typing import Annotated, List, File
from datetime import datetime

from app.services.auth import get_current_user
from services.ocr_client import parse_receipt_via_ocr_worker
from app.models.user import User
from app.models.transaction import Transaction , TransactionCreate, TransactionResponse
from app.models.receipt import Receipt, ReceiptItem
from database.db_setup import get_db


router = APIRouter(tags="")

@router.post("finance/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
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


@router.get("finance/transactions", response_model=List[TransactionResponse])
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


@router.post("/finance/upload-receipt", status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    file: Annotated[UploadFile, File()], 
    db: Annotated[Session, Depends(get_db)],
    # current_user: Annotated[User, Depends(get_current_user)] # Załóżmy, że używasz uwierzytelnienia
):
    # 1. Wyślij plik do pracownika OCR
    ocr_result = await parse_receipt_via_ocr_worker(file)

    # 2. Parsowanie i zapis nagłówka (Receipt)
    try:
        receipt_data = ocr_result.get("receipt_data", {})
        items_data = ocr_result.get("items", [])
        
        # Utwórz nowy obiekt Receipt
        new_receipt = Receipt(
            # user_id=current_user.id, # Powiąż z zalogowanym użytkownikiem
            user_id=1, # Na potrzeby testów, zakładając, że user_id=1 istnieje
            store_name=receipt_data.get("store", "Nieznany Sklep"),
            total_amount=receipt_data.get("total", 0.0),
            # Załóżmy, że data jest zwracana w formacie YYYY-MM-DD
            receipt_date=datetime.strptime(receipt_data.get("date", "2024-01-01"), "%Y-%m-%d"), 
        )
        
        db.add(new_receipt)
        db.flush() # Wymuś zapis, aby otrzymać new_receipt.id
        
        # 3. Parsowanie i zapis pozycji (ReceiptItem)
        for item in items_data:
            new_item = ReceiptItem(
                receipt_id=new_receipt.id,
                name=item.get("name"),
                quantity=item.get("qty", 1.0),
                price=item.get("unit_price", item.get("total_price")), # Zapisz cenę jednostkową
                total_price=item.get("total_price"),
            )
            db.add(new_item)
            
        db.commit()
        db.refresh(new_receipt)
        
        return {"message": "Paragon sparsowany i zapisany pomyślnie!", "receipt_id": new_receipt.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Błąd podczas zapisu danych z paragonu: {e}"
        )