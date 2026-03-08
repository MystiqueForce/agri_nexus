"""
Market Agent Test Script
-------------------------
Run: python tests/test_market_agent.py
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_sell_now_or_wait():
    """Test sell-now-or-wait scenario."""
    from app.agents.market.market_agent import run_market_agent

    print("=" * 60)
    print("TEST 1: Sell Now or Wait")
    print("=" * 60)

    result = await run_market_agent(
        query="Should I sell my onions now?",
        farm_id="test_farm",
        crop="onion",
        quantity=500,
        location="Bangalore, Karnataka",
    )

    print(f"\nDecision: {result.get('decision', 'N/A')}")
    print(f"Recommendation: {result.get('recommendation', 'N/A')}")
    print(f"Confidence: {result.get('confidence', 0):.0%}")
    print(f"\nPrice Predictions:")
    for p in result.get("price_predictions", []):
        print(f"  {p['market']}: ₹{p.get('current_price', 0)} → ₹{p['predicted_price']}")
    print(f"\nArrival Predictions:")
    for a in result.get("arrival_predictions", []):
        print(f"  {a['market']}: {a['predicted_arrival']} tonnes ({a['supply_level']})")
    print(f"\n--- Full Response ---")
    print(result.get("final_response", "No response"))
    print()


async def test_best_mandi():
    """Test best mandi recommendation."""
    from app.agents.market.market_agent import run_market_agent

    print("=" * 60)
    print("TEST 2: Best Mandi Recommendation")
    print("=" * 60)

    result = await run_market_agent(
        query="Where should I sell tomatoes today?",
        farm_id="test_farm",
        crop="tomato",
        quantity=200,
        location="Kolar, Karnataka",
    )

    print(f"\nDecision: {result.get('decision', 'N/A')}")
    print(f"Recommendation: {result.get('recommendation', 'N/A')}")
    print(f"\n--- Full Response ---")
    print(result.get("final_response", "No response"))
    print()


async def test_distress_selling():
    """Test distress selling warning."""
    from app.agents.market.market_agent import run_market_agent

    print("=" * 60)
    print("TEST 3: Distress Selling Warning")
    print("=" * 60)

    result = await run_market_agent(
        query="I harvested tomatoes today. Should I sell immediately?",
        farm_id="test_farm",
        crop="tomato",
        quantity=300,
        location="Tumkur, Karnataka",
    )

    print(f"\nDecision: {result.get('decision', 'N/A')}")
    print(f"Recommendation: {result.get('recommendation', 'N/A')}")
    print(f"\n--- Full Response ---")
    print(result.get("final_response", "No response"))
    print()


async def test_no_location():
    """Test with missing location — should ask for it."""
    from app.agents.market.market_agent import run_market_agent

    print("=" * 60)
    print("TEST 4: Missing Location (Should Request)")
    print("=" * 60)

    result = await run_market_agent(
        query="Should I sell potatoes now?",
        farm_id="test_farm",
        crop="potato",
        quantity=100,
    )

    print(f"\nNeeds Location: {result.get('needs_location', False)}")
    print(f"Follow-up: {result.get('follow_up_question', 'N/A')}")
    print(f"\n--- Response ---")
    print(result.get("final_response", "No response"))
    print()


async def main():
    print("\n📊 NexusAgri Market Agent Tests\n")

    try:
        await test_sell_now_or_wait()
        await test_best_mandi()
        await test_distress_selling()
        await test_no_location()
        print("✅ All tests completed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
