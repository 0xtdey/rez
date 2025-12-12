"""
Wallet Funding Service

Auto-funds new user wallets with testnet USDC.
Uses a platform-controlled master wallet to transfer funds.
"""

import os
import logging
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
import json

from trading.hyperliquid_real import HyperliquidClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default funding amount in USDC
DEFAULT_FUNDING_AMOUNT = 1000.0
MAX_FUNDING_PER_USER = 5000.0


@dataclass
class FundingRecord:
    """Record of a user funding event"""
    user_id: str
    wallet_address: str
    amount: float
    tx_hash: Optional[str]
    timestamp: str
    status: str  # "pending", "completed", "failed"


class UserStore:
    """
    Simple JSON-based user storage.
    Replace with PostgreSQL for production.
    """
    
    def __init__(self, storage_path: str = "data/users.json"):
        self.storage_path = storage_path
        self._ensure_storage()
    
    def _ensure_storage(self):
        """Ensure storage file exists"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, 'w') as f:
                json.dump({"users": {}, "funding_records": []}, f)
    
    def _load(self) -> dict:
        with open(self.storage_path, 'r') as f:
            return json.load(f)
    
    def _save(self, data: dict):
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_user(self, privy_user_id: str) -> Optional[dict]:
        """Get user by Privy user ID"""
        data = self._load()
        return data["users"].get(privy_user_id)
    
    def get_user_by_wallet(self, wallet_address: str) -> Optional[dict]:
        """Get user by wallet address"""
        data = self._load()
        for user in data["users"].values():
            if user.get("wallet_address", "").lower() == wallet_address.lower():
                return user
        return None
    
    def create_user(self, privy_user_id: str, email: Optional[str], wallet_address: str) -> dict:
        """Create a new user"""
        data = self._load()
        
        user = {
            "privy_user_id": privy_user_id,
            "email": email,
            "wallet_address": wallet_address,
            "created_at": datetime.utcnow().isoformat(),
            "funded_at": None,
            "total_funded": 0.0,
            "agent_approved": False,
            "agent_wallet": None
        }
        
        data["users"][privy_user_id] = user
        self._save(data)
        
        logger.info(f"Created user: {privy_user_id} with wallet {wallet_address}")
        return user
    
    def update_user(self, privy_user_id: str, updates: dict):
        """Update user fields"""
        data = self._load()
        if privy_user_id in data["users"]:
            data["users"][privy_user_id].update(updates)
            self._save(data)
    
    def record_funding(self, record: FundingRecord):
        """Record a funding event"""
        data = self._load()
        data["funding_records"].append({
            "user_id": record.user_id,
            "wallet_address": record.wallet_address,
            "amount": record.amount,
            "tx_hash": record.tx_hash,
            "timestamp": record.timestamp,
            "status": record.status
        })
        self._save(data)
    
    def get_user_funding_total(self, privy_user_id: str) -> float:
        """Get total funding for a user"""
        user = self.get_user(privy_user_id)
        return user.get("total_funded", 0.0) if user else 0.0


class FundingService:
    """
    Service to auto-fund new user wallets with testnet USDC.
    
    Flow:
    1. User logs in via Privy → Frontend calls /api/users/register
    2. Backend creates user record → Triggers funding
    3. Master wallet transfers USDC to user's embedded wallet
    4. User can now trade on Hyperliquid
    """
    
    def __init__(self, funding_amount: float = DEFAULT_FUNDING_AMOUNT):
        """
        Initialize FundingService.
        
        Args:
            funding_amount: Amount of testnet USDC to give each user
        """
        self.funding_amount = funding_amount
        self.user_store = UserStore()
        
        # Master wallet for funding (platform-controlled)
        self.master_wallet_key = os.getenv("FUNDING_WALLET_PRIVATE_KEY")
        self.master_wallet_client: Optional[HyperliquidClient] = None
        
        if self.master_wallet_key:
            try:
                self.master_wallet_client = HyperliquidClient(
                    private_key=self.master_wallet_key,
                    master_address=None  # Use key's address
                )
                logger.info("FundingService initialized with master wallet")
            except Exception as e:
                logger.warning(f"Could not initialize master wallet: {e}")
        else:
            logger.warning("FUNDING_WALLET_PRIVATE_KEY not set - funding disabled")
    
    def register_user(
        self,
        privy_user_id: str,
        email: Optional[str],
        wallet_address: str
    ) -> dict:
        """
        Register a new user and initiate funding.
        
        Args:
            privy_user_id: Privy user ID
            email: User email (if available)
            wallet_address: Embedded wallet address from Privy
        
        Returns:
            User record with funding status
        """
        # Check if user already exists
        existing = self.user_store.get_user(privy_user_id)
        if existing:
            logger.info(f"User {privy_user_id} already exists")
            return existing
        
        # Create new user
        user = self.user_store.create_user(privy_user_id, email, wallet_address)
        
        # Attempt to fund the wallet
        funding_result = self.fund_wallet(privy_user_id, wallet_address)
        
        return {
            **user,
            "funding_status": funding_result.status,
            "funding_amount": funding_result.amount if funding_result.status == "completed" else 0
        }
    
    def fund_wallet(self, user_id: str, wallet_address: str) -> FundingRecord:
        """
        Transfer testnet USDC to user's wallet.
        
        Args:
            user_id: Privy user ID
            wallet_address: Destination wallet address
        
        Returns:
            FundingRecord with status
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Check funding limits
        current_total = self.user_store.get_user_funding_total(user_id)
        if current_total >= MAX_FUNDING_PER_USER:
            logger.warning(f"User {user_id} has reached funding limit")
            record = FundingRecord(
                user_id=user_id,
                wallet_address=wallet_address,
                amount=0,
                tx_hash=None,
                timestamp=timestamp,
                status="limit_reached"
            )
            self.user_store.record_funding(record)
            return record
        
        # Check if master wallet is configured
        if not self.master_wallet_client:
            logger.warning("Master wallet not configured - simulating funding")
            record = FundingRecord(
                user_id=user_id,
                wallet_address=wallet_address,
                amount=self.funding_amount,
                tx_hash="simulated_" + timestamp.replace(":", "_"),
                timestamp=timestamp,
                status="simulated"
            )
            self.user_store.record_funding(record)
            self.user_store.update_user(user_id, {
                "funded_at": timestamp,
                "total_funded": current_total + self.funding_amount
            })
            return record
        
        # Execute transfer on Hyperliquid
        try:
            # Note: Hyperliquid testnet USDC transfer
            # The exact method depends on Hyperliquid's API
            # This is a placeholder for the actual implementation
            
            # For testnet, we might need to use a different approach:
            # Option 1: Transfer via Hyperliquid's internal transfer
            # Option 2: Transfer via Arbitrum Sepolia (requires bridging)
            
            logger.info(f"Transferring {self.funding_amount} USDC to {wallet_address}")
            
            # Placeholder - actual implementation depends on Hyperliquid's transfer API
            # result = self.master_wallet_client.transfer(
            #     to_address=wallet_address,
            #     amount=self.funding_amount
            # )
            
            # For now, mark as simulated until we implement actual transfers
            record = FundingRecord(
                user_id=user_id,
                wallet_address=wallet_address,
                amount=self.funding_amount,
                tx_hash=f"pending_{timestamp}",
                timestamp=timestamp,
                status="pending_manual"  # Requires manual funding for now
            )
            
            self.user_store.record_funding(record)
            self.user_store.update_user(user_id, {
                "funded_at": timestamp,
                "total_funded": current_total + self.funding_amount
            })
            
            logger.info(f"Funding recorded for {wallet_address}")
            return record
            
        except Exception as e:
            logger.error(f"Funding failed for {wallet_address}: {e}")
            record = FundingRecord(
                user_id=user_id,
                wallet_address=wallet_address,
                amount=0,
                tx_hash=None,
                timestamp=timestamp,
                status="failed"
            )
            self.user_store.record_funding(record)
            return record
    
    def get_user_status(self, privy_user_id: str) -> Optional[dict]:
        """Get user status including funding info"""
        user = self.user_store.get_user(privy_user_id)
        if not user:
            return None
        
        return {
            "user_id": user["privy_user_id"],
            "wallet_address": user["wallet_address"],
            "funded": user["funded_at"] is not None,
            "total_funded": user["total_funded"],
            "agent_approved": user["agent_approved"],
            "created_at": user["created_at"]
        }


# Factory function
def create_funding_service() -> FundingService:
    """Create FundingService with default configuration"""
    amount = float(os.getenv("FUNDING_AMOUNT_USDC", DEFAULT_FUNDING_AMOUNT))
    return FundingService(funding_amount=amount)
