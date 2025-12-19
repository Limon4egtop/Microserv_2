from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Literal

OrderStatus = Literal["created", "in_progress", "completed", "cancelled"]

class OrderItem(BaseModel):
    product: str = Field(min_length=1)
    quantity: int = Field(ge=1)

class CreateOrderRequest(BaseModel):
    items: List[OrderItem] = Field(min_length=1)
    total_sum: float = Field(ge=0)

class UpdateStatusRequest(BaseModel):
    status: OrderStatus
