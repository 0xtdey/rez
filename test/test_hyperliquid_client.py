#!/usr/bin/env python3
"""
Test script for Hyperliquid SDK integration.
Run this to verify connectivity and basic operations before trading.

Usage:
    python test/test_hyperliquid_client.py
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()

from trading.hyperliquid_real import HyperliquidClient, create_client


def test_health_check():
    """Test API connectivity"""
    print("\n=== Testing Health Check ===")
    try:
        client = create_client()
        healthy = client.health_check()
        print(f"✅ API Health: {'OK' if healthy else 'FAILED'}")
        return healthy
    except ValueError as e:
        print(f"⚠️  Configuration error: {e}")
        print("   Please set HL_PRIVATE_KEY and HL_MASTER_ADDRESS in .env")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_get_price():
    """Test getting current prices"""
    print("\n=== Testing Price Fetch ===")
    try:
        client = create_client()
        btc_price = client.get_current_price("BTC")
        eth_price = client.get_current_price("ETH")
        print(f"✅ BTC price: ${btc_price:,.2f}")
        print(f"✅ ETH price: ${eth_price:,.2f}")
        return True
    except Exception as e:
        print(f"❌ Price fetch failed: {e}")
        return False


def test_portfolio_state():
    """Test getting portfolio state"""
    print("\n=== Testing Portfolio State ===")
    try:
        client = create_client()
        state = client.get_portfolio_state()
        print(f"✅ Account Value: ${state.account_value:,.2f}")
        print(f"✅ Available Balance: ${state.available_balance:,.2f}")
        print(f"✅ Open Positions: {len(state.positions)}")
        for pos in state.positions:
            print(f"   - {pos.asset}: {pos.size} ({pos.side}) @ ${pos.entry_price:,.2f}")
        return True
    except Exception as e:
        print(f"❌ Portfolio state failed: {e}")
        return False


def test_order_placement(dry_run: bool = True):
    """Test order placement (dry run by default)"""
    print(f"\n=== Testing Order Placement {'(DRY RUN)' if dry_run else '(LIVE)'} ===")
    
    if dry_run:
        print("⚠️  Dry run mode - no actual order placed")
        print("   To test real orders, call with dry_run=False")
        return True
    
    try:
        client = create_client()
        
        # Place tiny order on testnet
        result = client.place_order(
            asset="BTC",
            is_buy=True,
            size=0.001,  # Minimum size
            price=None   # Market order
        )
        
        if result.success:
            print(f"✅ Order placed: {result.order_id}")
            print(f"   Status: {result.status}")
            print(f"   Filled: {result.filled_size} @ ${result.avg_price:,.2f}")
        else:
            print(f"❌ Order failed: {result.error}")
        
        return result.success
    except Exception as e:
        print(f"❌ Order placement failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 50)
    print("Hyperliquid SDK Integration Tests")
    print("=" * 50)
    
    # Check environment
    print("\n=== Checking Environment ===")
    hl_testnet = os.getenv("HL_TESTNET", "true")
    hl_key_set = bool(os.getenv("HL_PRIVATE_KEY"))
    hl_addr_set = bool(os.getenv("HL_MASTER_ADDRESS"))
    
    print(f"Network: {'TESTNET' if hl_testnet.lower() == 'true' else 'MAINNET'}")
    print(f"Private Key: {'✅ Set' if hl_key_set else '❌ Not set'}")
    print(f"Master Address: {'✅ Set' if hl_addr_set else '❌ Not set'}")
    
    if not hl_key_set or not hl_addr_set:
        print("\n⚠️  Please configure Hyperliquid credentials in .env file")
        print("   See .env.example for required variables")
        return
    
    # Run tests
    results = {
        "Health Check": test_health_check(),
        "Price Fetch": test_get_price(),
        "Portfolio State": test_portfolio_state(),
        "Order Placement": test_order_placement(dry_run=True)
    }
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'✅ All tests passed!' if all_passed else '❌ Some tests failed'}")


if __name__ == "__main__":
    main()
