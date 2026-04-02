"""make projects.owner_id not null

Revision ID: a1b2c3d4e5f6
Revises: d4e5f6a7b8c9
Create Date: 2026-04-02 23:30:00.000000
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            fallback_user_id UUID;
        BEGIN
            SELECT id INTO fallback_user_id
            FROM users
            ORDER BY created_at ASC
            LIMIT 1;

            IF fallback_user_id IS NULL THEN
                INSERT INTO users (id, login_id, email, password_hash, display_name, is_active, role)
                VALUES (
                    '00000000-0000-0000-0000-000000000001',
                    'system-owner',
                    'system-owner@local.invalid',
                    NULL,
                    'System Owner',
                    TRUE,
                    'SYSTEM'
                )
                RETURNING id INTO fallback_user_id;
            END IF;

            UPDATE projects
            SET owner_id = fallback_user_id
            WHERE owner_id IS NULL;

            ALTER TABLE projects
            ALTER COLUMN owner_id SET NOT NULL;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE projects
        ALTER COLUMN owner_id DROP NOT NULL;
        """
    )
