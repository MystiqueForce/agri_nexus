"""
Health Agent Test Script
-------------------------
Run: python tests/test_health_agent.py
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_text_diagnosis():
    """Test text-based health diagnosis."""
    from app.agents.health.health_agent import run_health_agent

    print("=" * 60)
    print("TEST 1: Text-based Crop Diagnosis")
    print("=" * 60)

    result = await run_health_agent(
        query="My tomato leaves have black spots and the plant looks weak",
        farm_id="test_farm",
    )

    print(f"\nDiagnosis: {result.get('top_diagnosis', 'N/A')}")
    print(f"Confidence: {result.get('top_confidence', 0):.0%}")
    print(f"Severity: {result.get('severity', 'N/A')}")
    print(f"Domain: {result.get('domain', 'N/A')}")
    print(f"Entity: {result.get('entity', 'N/A')}")
    print(f"Symptoms: {result.get('symptoms', [])}")
    print(f"\n--- Full Response ---")
    print(result.get("final_response", "No response"))
    print()


async def test_livestock_diagnosis():
    """Test livestock health diagnosis."""
    from app.agents.health.health_agent import run_health_agent

    print("=" * 60)
    print("TEST 2: Livestock Diagnosis")
    print("=" * 60)

    result = await run_health_agent(
        query="My cow has fever and not eating since yesterday",
        farm_id="test_farm",
    )

    print(f"\nDiagnosis: {result.get('top_diagnosis', 'N/A')}")
    print(f"Confidence: {result.get('top_confidence', 0):.0%}")
    print(f"Severity: {result.get('severity', 'N/A')}")
    print(f"Domain: {result.get('domain', 'N/A')}")
    print(f"Needs Follow-up: {result.get('needs_follow_up', False)}")

    if result.get("needs_follow_up"):
        print(f"Follow-up Question: {result.get('follow_up_question', '')}")
    else:
        print(f"\n--- Full Response ---")
        print(result.get("final_response", "No response"))
    print()


async def test_ambiguous_query():
    """Test with ambiguous query to trigger follow-up."""
    from app.agents.health.health_agent import run_health_agent

    print("=" * 60)
    print("TEST 3: Ambiguous Query (May Trigger Follow-up)")
    print("=" * 60)

    result = await run_health_agent(
        query="My plant looks bad",
        farm_id="test_farm",
    )

    print(f"\nDiagnosis: {result.get('top_diagnosis', 'N/A')}")
    print(f"Confidence: {result.get('top_confidence', 0):.0%}")
    print(f"Needs Follow-up: {result.get('needs_follow_up', False)}")

    if result.get("needs_follow_up"):
        print(f"Follow-up Question: {result.get('follow_up_question', '')}")
    else:
        print(f"Severity: {result.get('severity', 'N/A')}")
        print(f"\n--- Full Response ---")
        print(result.get("final_response", "No response"))
    print()


async def main():
    print("\n🌿 NexusAgri Health Agent Tests\n")

    try:
        await test_text_diagnosis()
        await test_livestock_diagnosis()
        await test_ambiguous_query()
        print("✅ All tests completed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("Make sure AWS credentials are configured.")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
