"""Add AI review tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- ai_review_results ---
    op.create_table(
        'ai_review_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dlc_application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('verdict', sa.String(30), nullable=False, server_default='PENDING'),
        sa.Column('issues', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('enhanced_fields', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('compliance_flags', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('model_used', sa.String(50), nullable=False, server_default='gpt-4o'),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['dlc_application_id'], ['dlc_applications.id']),
    )
    op.create_index('ix_ai_review_results_dlc_application_id', 'ai_review_results', ['dlc_application_id'])

    # --- ai_review_prompts ---
    op.create_table(
        'ai_review_prompts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('prompt_type', sa.String(30), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('model', sa.String(50), nullable=False, server_default='gpt-4o'),
        sa.Column('temperature', sa.Float(), nullable=False, server_default='0.3'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )
    op.create_index('ix_ai_review_prompts_prompt_type', 'ai_review_prompts', ['prompt_type'])


def downgrade() -> None:
    op.drop_index('ix_ai_review_prompts_prompt_type', table_name='ai_review_prompts')
    op.drop_table('ai_review_prompts')
    op.drop_index('ix_ai_review_results_dlc_application_id', table_name='ai_review_results')
    op.drop_table('ai_review_results')
