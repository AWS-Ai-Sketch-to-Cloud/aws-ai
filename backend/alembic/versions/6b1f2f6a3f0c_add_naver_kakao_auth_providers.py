"""add naver and kakao auth providers

Revision ID: 6b1f2f6a3f0c
Revises: 01898398e88a
Create Date: 2026-03-30 14:45:00.000000
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "6b1f2f6a3f0c"
down_revision = "01898398e88a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = 'auth_identities'
                  AND constraint_name = 'auth_identities_provider_check'
                  AND constraint_type = 'CHECK'
            ) THEN
                ALTER TABLE auth_identities
                DROP CONSTRAINT auth_identities_provider_check;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        ALTER TABLE auth_identities
        ADD CONSTRAINT auth_identities_provider_check
        CHECK (provider IN ('LOCAL', 'GOOGLE', 'GITHUB', 'NAVER', 'KAKAO'));
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = 'auth_identities'
                  AND constraint_name = 'auth_identities_provider_check'
                  AND constraint_type = 'CHECK'
            ) THEN
                ALTER TABLE auth_identities
                DROP CONSTRAINT auth_identities_provider_check;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        ALTER TABLE auth_identities
        ADD CONSTRAINT auth_identities_provider_check
        CHECK (provider IN ('LOCAL', 'GOOGLE', 'GITHUB'));
        """
    )
