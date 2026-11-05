"""Initial schema.

Revision ID: 0001_initial
Revises: None
"""

from alembic import op
import sqlalchemy as sa

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(320), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_table(
        'favorites',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_type', sa.String(20), nullable=False),
        sa.Column('entity_id', sa.String(80), nullable=False),
        sa.Column('label', sa.String(120), nullable=False),
        sa.UniqueConstraint('user_id', 'entity_type', 'entity_id', name='uq_favorite'),
    )
    op.create_table(
        'match_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('external_match_id', sa.String(80), nullable=False),
        sa.Column('competition_code', sa.String(20), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column(
            'captured_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        'ix_match_snapshots_external_match_id',
        'match_snapshots',
        ['external_match_id'],
    )
    op.create_index(
        'ix_match_snapshots_competition_code',
        'match_snapshots',
        ['competition_code'],
    )
    op.create_index('ix_match_snapshots_status', 'match_snapshots', ['status'])
    op.create_index('ix_match_snapshots_captured_at', 'match_snapshots', ['captured_at'])


def downgrade():
    op.drop_table('match_snapshots')
    op.drop_table('favorites')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
