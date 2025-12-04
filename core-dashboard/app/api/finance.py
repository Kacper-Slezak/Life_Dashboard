from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from typing import Annotated, List
from datetime import datetime

from app.services.auth import get_current_user
from app.services.ocr_client import parse_receipt_via_ocr_worker # FIX: Changed from 'services.ocr_client' to 'app.services.ocr_client'
from app.models.user import User
from app.models.transaction import Transaction , TransactionCreate, TransactionResponse
from app.models.receipt import Receipt, ReceiptItem
from database.db_setup import get_db


router = APIRouter(prefix="/finance")


@router.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
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


@router.get("/transactions", response_model=List[TransactionResponse])
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


@router.post("/upload-receipt", status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    file: Annotated[UploadFile, Depends()],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    ocr_result = await parse_receipt_via_ocr_worker(file)

    parsed_data = ocr_result.get('parsed_data', {})
    receipt_data = parsed_data.get("receipt_data", {})
    items_data = parsed_data.get("items", [])

    try:
        final_parsed_data = ocr_result.get('parsed_data', {})

        store_name = final_parsed_data.get("store", "Unknown Store")
        total_amount = float(final_parsed_data.get("total") or 0.0) # Convert total to float, defaulting to 0.0 if None
        items_data = final_parsed_data.get("items", [])

        # Attempt to parse date, default to today if missing or invalid
        date_str = final_parsed_data.get("date")
        receipt_date = datetime.now().date()
        if date_str:
            try:
                # Assuming date is returned in a standard format, e.g., YYYY-MM-DD
                receipt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                # Attempt to extract date from raw_text or log error if needed
                pass 
        
        new_receipt = Receipt(
            user_id=current_user.id,
            store_name=store_name,
            total_amount=total_amount,
            receipt_date=receipt_date,
        )
        
        db.add(new_receipt)
        db.flush() 
        for item in items_data:
            try:
                # Safely convert strings from OCR data to floats
                total_price_float = float(item.get("total_price", 0.0))
                
                # Unit price may not exist, default to total price or 0.0
                unit_price_str = item.get("unit_price")
                if unit_price_str:
                     price_float = float(unit_price_str)
                else:
                     price_float = total_price_float # If unit price is missing, assume it's the same as total
                
                # Quantity defaults to 1.0
                quantity_float = float(item.get("quantity", 1.0))
                
            except (ValueError, TypeError) as e:
                print(f"Warning: Failed to convert price/quantity for item {item.get('name')}: {e}")
                total_price_float = 0.0
                price_float = 0.0
                quantity_float = 1.0
                
            new_item = ReceiptItem(
                receipt_id=new_receipt.id,
                name=item.get("name", "Unknown Item"),
                quantity=quantity_float,
                price=price_float, 
                total_price=total_price_float,
            )
            db.add(new_item)
            
        db.commit()
        db.refresh(new_receipt)
        
        return {"message": "Receipt parsed and saved successfully!", "receipt_id": new_receipt.id}
        
    except Exception as e:
        db.rollback()
        print(f"FATAL ERROR saving parsed receipt data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error saving data: {e}"
        )