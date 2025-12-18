"""
Database Integration Test
Tests database connectivity and table existence
"""
import asyncio
import sys
import os

# Add api app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'api'))

async def test_database_connection():
    """Test database is accessible and tables exist"""

    print("Testing database connection...")

    try:
        from sqlalchemy import text
        from app.core.database import engine

        async with engine.connect() as conn:
            # Test basic connection
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
            print("  [OK] Database connection successful")

            # Check tables exist
            result = await conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]

            print(f"  [OK] Found {len(tables)} tables")

            required_tables = ['users', 'identities', 'actor_packs', 'licenses', 'usage_logs', 'api_keys', 'listings']

            for table in required_tables:
                if table in tables:
                    print(f"      - {table}: exists")
                else:
                    print(f"      - {table}: MISSING!")

            # Test pgvector extension
            result = await conn.execute(text("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                )
            """))
            has_vector = result.scalar()

            if has_vector:
                print("  [OK] pgvector extension installed")
            else:
                print("  [WARN] pgvector extension not installed")

            return True

    except Exception as e:
        print(f"  [FAIL] Database error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_connection())
    sys.exit(0 if success else 1)
