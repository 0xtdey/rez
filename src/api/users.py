"""
User Management API Endpoints

Handles user registration, funding, and agent approval.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.funding import create_funding_service, FundingService

# Create router
router = APIRouter(prefix="/users", tags=["users"])

# Initialize funding service
funding_service = create_funding_service()


# Models
class UserRegistrationRequest(BaseModel):
    """Request to register a new user"""
    privy_user_id: str
    email: Optional[str] = None
    wallet_address: str


class UserStatusResponse(BaseModel):
    """User status response"""
    user_id: str
    wallet_address: str
    funded: bool
    total_funded: float
    agent_approved: bool
    created_at: str


class FundingResponse(BaseModel):
    """Funding result response"""
    status: str
    amount: float
    tx_hash: Optional[str] = None
    message: str


# Endpoints

@router.post("/register", response_model=dict)
async def register_user(request: UserRegistrationRequest):
    """
    Register a new user and initiate wallet funding.
    
    Called by frontend after Privy authentication.
    """
    try:
        result = funding_service.register_user(
            privy_user_id=request.privy_user_id,
            email=request.email,
            wallet_address=request.wallet_address
        )
        
        return {
            "status": "success",
            "user": result,
            "message": "User registered and funding initiated"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{privy_user_id}", response_model=UserStatusResponse)
async def get_user_status(privy_user_id: str):
    """
    Get user status including funding info.
    """
    status = funding_service.get_user_status(privy_user_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserStatusResponse(**status)


@router.post("/fund/{privy_user_id}", response_model=FundingResponse)
async def request_funding(privy_user_id: str):
    """
    Request additional funding for a user (if within limits).
    """
    user = funding_service.user_store.get_user(privy_user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = funding_service.fund_wallet(
        user_id=privy_user_id,
        wallet_address=user["wallet_address"]
    )
    
    return FundingResponse(
        status=result.status,
        amount=result.amount,
        tx_hash=result.tx_hash,
        message=f"Funding {result.status} for {user['wallet_address']}"
    )


@router.post("/approve-agent/{privy_user_id}")
async def approve_agent(privy_user_id: str, agent_wallet: str):
    """
    Record that user has approved an agent wallet for trading.
    
    Called after user signs approval transaction via Privy.
    """
    user = funding_service.user_store.get_user(privy_user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    funding_service.user_store.update_user(privy_user_id, {
        "agent_approved": True,
        "agent_wallet": agent_wallet
    })
    
    return {
        "status": "success",
        "message": f"Agent wallet {agent_wallet} approved for trading"
    }


@router.get("/all")
async def list_all_users():
    """
    List all registered users (admin endpoint).
    """
    data = funding_service.user_store._load()
    return {
        "users": list(data["users"].values()),
        "total_count": len(data["users"])
    }
