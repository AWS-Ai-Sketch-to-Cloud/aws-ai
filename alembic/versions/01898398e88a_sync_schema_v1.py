"""sync schema v1

Revision ID: 01898398e88a
Revises: 
Create Date: 2026-03-20 16:44:14.375513
"""
from __future__ import annotations

from alembic import op



# revision identifiers, used by Alembic.
revision = '01898398e88a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'projects'
                  AND column_name = 'owner_id'
                  AND data_type <> 'uuid'
            ) THEN
                UPDATE projects
                SET owner_id = NULL
                WHERE owner_id IS NOT NULL
                  AND owner_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$';

                ALTER TABLE projects
                ALTER COLUMN owner_id TYPE UUID
                USING owner_id::uuid;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = 'projects'
                  AND constraint_name = 'fk_projects_owner_id_users'
                  AND constraint_type = 'FOREIGN KEY'
            ) THEN
                ALTER TABLE projects
                ADD CONSTRAINT fk_projects_owner_id_users
                FOREIGN KEY (owner_id) REFERENCES users(id)
                ON DELETE CASCADE;
            END IF;
        END
        $$;
        """
    )

    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS contract_version;")


def downgrade() -> None:
    op.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS contract_version VARCHAR(20) DEFAULT 'v1' NOT NULL;")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = 'projects'
                  AND constraint_name = 'fk_projects_owner_id_users'
                  AND constraint_type = 'FOREIGN KEY'
            ) THEN
                ALTER TABLE projects
                DROP CONSTRAINT fk_projects_owner_id_users;
            END IF;
        END
        $$;
        """
    )

