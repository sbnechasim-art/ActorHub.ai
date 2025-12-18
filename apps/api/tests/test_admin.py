"""
Tests for Admin Endpoints
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole, UserTier
from app.models.identity import Identity
from app.models.notifications import AuditLog, AuditAction


@pytest.fixture
async def multiple_users(db_session: AsyncSession):
    """Create multiple users for admin tests"""
    from app.core.security import hash_password

    users = []
    for i in range(5):
        user = User(
            email=f"user{i}@example.com",
            hashed_password=hash_password(f"password{i}"),
            first_name=f"User{i}",
            last_name="Test",
            is_active=True if i % 2 == 0 else False,
            role=UserRole.USER,
            tier=UserTier.FREE if i < 3 else UserTier.PRO,
        )
        db_session.add(user)
        users.append(user)
    await db_session.commit()
    return users


@pytest.fixture
async def test_audit_logs(db_session: AsyncSession, test_user: User):
    """Create test audit logs"""
    logs = [
        AuditLog(
            user_id=test_user.id,
            action=AuditAction.LOGIN,
            resource_type="session",
            ip_address="192.168.1.1",
            success=True,
        ),
        AuditLog(
            user_id=test_user.id,
            action=AuditAction.CREATE,
            resource_type="identity",
            success=True,
        ),
        AuditLog(
            user_id=test_user.id,
            action=AuditAction.API_CALL,
            resource_type="verification",
            success=False,
            error_message="Rate limited",
        ),
    ]
    for log in logs:
        db_session.add(log)
    await db_session.commit()
    return logs


class TestAdminAccess:
    """Test admin access control"""

    @pytest.mark.asyncio
    async def test_admin_dashboard_requires_admin(self, auth_client: AsyncClient):
        """Test that dashboard requires admin role"""
        response = await auth_client.get("/api/v1/admin/dashboard")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_dashboard_accessible_to_admin(
        self, admin_client: AsyncClient
    ):
        """Test that admin can access dashboard"""
        response = await admin_client.get("/api/v1/admin/dashboard")
        assert response.status_code == 200

        data = response.json()
        assert "total_users" in data
        assert "active_users" in data
        assert "total_identities" in data

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """Test that unauthenticated requests are rejected"""
        response = await client.get("/api/v1/admin/dashboard")
        assert response.status_code == 401


class TestAdminUserManagement:
    """Test admin user management endpoints"""

    @pytest.mark.asyncio
    async def test_list_users(
        self, admin_client: AsyncClient, multiple_users
    ):
        """Test listing all users"""
        response = await admin_client.get("/api/v1/admin/users")
        assert response.status_code == 200

        data = response.json()
        assert "users" in data
        assert "total" in data
        # 5 test users + admin user
        assert data["total"] >= 5

    @pytest.mark.asyncio
    async def test_list_users_with_filter(
        self, admin_client: AsyncClient, multiple_users
    ):
        """Test filtering users by tier"""
        response = await admin_client.get("/api/v1/admin/users?tier=PRO")
        assert response.status_code == 200

        data = response.json()
        for user in data["users"]:
            assert user["tier"] == "PRO"

    @pytest.mark.asyncio
    async def test_list_users_with_search(
        self, admin_client: AsyncClient, multiple_users
    ):
        """Test searching users by email"""
        response = await admin_client.get("/api/v1/admin/users?search=user2")
        assert response.status_code == 200

        data = response.json()
        assert len(data["users"]) >= 1
        assert "user2" in data["users"][0]["email"]

    @pytest.mark.asyncio
    async def test_get_user_details(
        self, admin_client: AsyncClient, test_user: User
    ):
        """Test getting user details"""
        response = await admin_client.get(f"/api/v1/admin/users/{test_user.id}")
        assert response.status_code == 200

        data = response.json()
        assert "user" in data
        assert "stats" in data
        assert data["user"]["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_update_user(
        self, admin_client: AsyncClient, test_user: User
    ):
        """Test updating a user"""
        response = await admin_client.patch(
            f"/api/v1/admin/users/{test_user.id}",
            params={"tier": "PRO", "is_active": True}
        )
        assert response.status_code == 200

        # Verify update
        response = await admin_client.get(f"/api/v1/admin/users/{test_user.id}")
        assert response.json()["user"]["tier"] == "PRO"

    @pytest.mark.asyncio
    async def test_cannot_demote_self(self, admin_client: AsyncClient, admin_user: User):
        """Test that admin cannot demote themselves"""
        response = await admin_client.patch(
            f"/api/v1/admin/users/{admin_user.id}",
            params={"role": "USER"}
        )
        assert response.status_code == 400
        assert "demote yourself" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_user_not_found(self, admin_client: AsyncClient):
        """Test getting non-existent user"""
        import uuid
        response = await admin_client.get(f"/api/v1/admin/users/{uuid.uuid4()}")
        assert response.status_code == 404


class TestAdminAuditLogs:
    """Test admin audit log endpoints"""

    @pytest.mark.asyncio
    async def test_get_audit_logs(
        self, admin_client: AsyncClient, test_audit_logs
    ):
        """Test getting audit logs"""
        response = await admin_client.get("/api/v1/admin/audit-logs")
        assert response.status_code == 200

        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert len(data["logs"]) >= 3

    @pytest.mark.asyncio
    async def test_filter_audit_logs_by_action(
        self, admin_client: AsyncClient, test_audit_logs
    ):
        """Test filtering audit logs by action"""
        response = await admin_client.get("/api/v1/admin/audit-logs?action=LOGIN")
        assert response.status_code == 200

        data = response.json()
        for log in data["logs"]:
            assert log["action"] == "LOGIN"

    @pytest.mark.asyncio
    async def test_filter_audit_logs_by_resource(
        self, admin_client: AsyncClient, test_audit_logs
    ):
        """Test filtering audit logs by resource type"""
        response = await admin_client.get(
            "/api/v1/admin/audit-logs?resource_type=identity"
        )
        assert response.status_code == 200

        data = response.json()
        for log in data["logs"]:
            assert log["resource_type"] == "identity"

    @pytest.mark.asyncio
    async def test_regular_user_cannot_access_audit_logs(
        self, auth_client: AsyncClient
    ):
        """Test that regular users cannot access audit logs"""
        response = await auth_client.get("/api/v1/admin/audit-logs")
        assert response.status_code == 403
