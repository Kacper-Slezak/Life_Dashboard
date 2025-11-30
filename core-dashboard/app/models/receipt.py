# core-dashboard/app/models/receipt.py

from sqlalchemy import Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import List
from database.db_setup import Base 


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    
    store_name: Mapped[str | None] = mapped_column(String(100), index=True)
    receipt_date: Mapped[DateTime | None] = mapped_column(DateTime)
    total_amount: Mapped[float] = mapped_column(Float)
    
    items: Mapped[List["ReceiptItem"]] = relationship(back_populates="receipt", cascade="all, delete-orphan")


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    receipt_id: Mapped[int] = mapped_column(Integer, ForeignKey("receipts.id"))
    

    name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    price: Mapped[float] = mapped_column(Float) 
    total_price: Mapped[float] = mapped_column(Float)
    
    receipt: Mapped["Receipt"] = relationship(back_populates="items")
    