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
    Creates a new financial transaction for the logged-in user.
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
    Retrieves a list of all financial transactions for the logged-in user.
    """
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.date.desc()).all()
    
    return transactions


@router.post("/finance/upload-receipt", status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    file: Annotated[UploadFile, File()], 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    ocr_result = await parse_receipt_via_ocr_worker(file)

    parsed_data = ocr_result.get('parsed_data', {})
    receipt_data = parsed_data.get("receipt_data", {})
    items_data = parsed_data.get("items", [])

    try:
        receipt_data = ocr_result.get("receipt_data", {})
        items_data = ocr_result.get("items", [])
        
        new_receipt = Receipt(
            user_id=current_user.id,
            store_name=receipt_data.get("store", "Unknown Store"),
            total_amount=receipt_data.get("total", 0.0),
            receipt_date=datetime.strptime(parsed_data.get("date", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d").date(),
        )
        
        db.add(new_receipt)
        db.flush() 
        for item in items_data:
            try:
                total_price_float = float(item.get("total_price", 0.0))
                price_float = float(item.get("unit_price", total_price_float))
            except (ValueError, TypeError):
                total_price_float = 0.0
                price_float = 0.0
                
            new_item = ReceiptItem(
                receipt_id=new_receipt.id,
                name=item.get("name"),
                quantity=item.get("quantity", 1.0),
                price=price_float, 
                total_price=total_price_float,
            )
            db.add(new_item)
            
        db.commit()
        db.refresh(new_receipt)
        
        return {"message": "Receipt parsed and saved successfully!", "receipt_id": new_receipt.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error saving data: {e}"
        )