# Database Migrations

This folder contains Alembic database migrations for ActorHub.ai.

## Migration Chain

```
001_initial_schema
    └── 91fd970f8f07_add_2fa_and_gdpr_fields_to_users
            └── 20251217_add_missing_indexes
                    └── 20251218_notifications (20251218_add_notifications_audit_subscriptions)
                            └── 20251218_add_stripe_connect
```

## Migrations Overview

| Migration | Description | Tables Affected |
|-----------|-------------|-----------------|
| `001_initial_schema` | Initial database schema | users, identities, actor_packs, licenses, listings, transactions, usage_logs, api_keys |
| `91fd970f8f07_add_2fa...` | Add 2FA and GDPR fields | users |
| `20251217_add_missing_indexes` | Performance indexes | identities, licenses, listings |
| `20251218_notifications...` | Notifications, audit logs, subscriptions | notifications, audit_logs, subscriptions |
| `20251218_add_stripe_connect` | Stripe Connect account ID | users |

## Common Commands

```bash
# Check current revision
python -m alembic current

# Show migration history
python -m alembic history

# Upgrade to latest
python -m alembic upgrade head

# Upgrade one step
python -m alembic upgrade +1

# Downgrade one step
python -m alembic downgrade -1

# Downgrade to specific revision
python -m alembic downgrade <revision_id>

# Create new migration
python -m alembic revision --autogenerate -m "description"

# Stamp database without running migration
python -m alembic stamp <revision_id>
```

## Creating New Migrations

1. Make changes to SQLAlchemy models in `app/models/`
2. Generate migration:
   ```bash
   python -m alembic revision --autogenerate -m "descriptive_name"
   ```
3. Review the generated migration file
4. Test upgrade and downgrade:
   ```bash
   python -m alembic upgrade head
   python -m alembic downgrade -1
   python -m alembic upgrade head
   ```

## Migration Best Practices

1. **Always test both upgrade and downgrade** before committing
2. **Use descriptive names** for migrations
3. **Keep migrations small** - one logical change per migration
4. **Never edit migrations** that have been deployed to production
5. **Add proper indexes** for foreign keys and frequently queried columns
6. **Use `op.batch_alter_table()`** for SQLite compatibility (if needed)

## Fixing Migration Issues

### Wrong revision ID
If you see `alembic.util.exc.CommandError: Can't locate revision`:
```bash
# Check current state
python -m alembic current

# Stamp to correct revision
python -m alembic stamp <correct_revision_id>

# Then upgrade
python -m alembic upgrade head
```

### Table already exists
If migration fails with "table already exists":
```bash
# Stamp the migration as complete without running it
python -m alembic stamp <revision_id>
```

### Rolling back failed migration
```bash
# Downgrade to previous working state
python -m alembic downgrade <previous_revision>

# Fix the migration file, then retry
python -m alembic upgrade head
```

## Production Deployment

1. **Always backup the database** before running migrations
2. Run migrations during maintenance window
3. Test on staging environment first
4. Have rollback plan ready
5. Monitor database during migration

```bash
# Production migration sequence
pg_dump -h $DB_HOST -U $DB_USER $DB_NAME > backup_$(date +%Y%m%d).sql
python -m alembic upgrade head
```
