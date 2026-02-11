#!/usr/bin/env python3
"""Add credits to a user account for testing purposes."""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import SessionLocal


def add_credits_to_user(user_id: str, amount: int, description: str = "Testing grant"):
    """
    Add credits to a user account using the credit_user_balance stored procedure.

    Args:
        user_id: User UUID as string
        amount: Number of credits to add (positive integer)
        description: Transaction description
    """
    db = SessionLocal()
    try:
        print(f"🔄 Attempting to add {amount} credits to user {user_id}...")

        # Call the PostgreSQL stored procedure
        result = db.execute(
            text("""
                SELECT credit_user_balance(
                    :user_id::uuid,
                    :amount,
                    'grant',
                    NULL,
                    :description
                )
            """),
            {
                "user_id": user_id,
                "amount": amount,
                "description": description
            }
        )
        db.commit()

        # Get new balance
        balance_result = db.execute(
            text("""
                SELECT balance
                FROM user_credits
                WHERE user_id = :user_id::uuid
            """),
            {"user_id": user_id}
        ).fetchone()

        new_balance = balance_result[0] if balance_result else 0

        print(f"✅ Successfully added {amount} credits to user {user_id}")
        print(f"   New balance: {new_balance} credits")

        return new_balance

    except Exception as e:
        db.rollback()
        print(f"❌ Error adding credits: {e}")
        print(f"   Error type: {type(e).__name__}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # User ID from localStorage: b9b53e8a-64d0-41f7-81d5-6c53aa8325cb
    USER_ID = "b9b53e8a-64d0-41f7-81d5-6c53aa8325cb"
    CREDITS_TO_ADD = 50

    print(f"🚀 Credit Addition Script Starting...")
    print(f"   Target User: {USER_ID}")
    print(f"   Credits to Add: {CREDITS_TO_ADD}")
    print()

    try:
        final_balance = add_credits_to_user(
            USER_ID,
            CREDITS_TO_ADD,
            f"Admin grant for testing ({CREDITS_TO_ADD} credits)"
        )
        print()
        print(f"✅ Script completed successfully!")
        print(f"   Final balance: {final_balance} credits")
    except Exception as e:
        print()
        print(f"❌ Script failed: {e}")
        sys.exit(1)
