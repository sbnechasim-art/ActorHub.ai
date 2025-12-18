"""Test router imports"""
try:
    from app.api.v1 import router
    print(f"Total routes: {len(router.routes)}")
    for r in router.routes:
        print(f"  {getattr(r, 'path', 'N/A')}")
except Exception as e:
    print(f"Import error: {e}")
