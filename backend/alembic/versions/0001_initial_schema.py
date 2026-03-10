"""Initial schema for BlastWave SMS

Revision ID: 0001
Revises:
Create Date: 2026-03-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- tenants ---
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_item_id', sa.String(255), nullable=True),
        sa.Column('plan_tier', sa.String(50), nullable=False, server_default='free_trial'),
        sa.Column('credit_balance', sa.Numeric(12, 4), nullable=False, server_default='0'),
        sa.Column('bandwidth_site_id', sa.String(255), nullable=True),
        sa.Column('bandwidth_location_id', sa.String(255), nullable=True),
        sa.Column('bandwidth_application_id', sa.String(255), nullable=True),
        sa.Column('settings', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    # --- users ---
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(255), nullable=False),
        sa.Column('last_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='sender'),
        sa.Column('mfa_secret', sa.String(255), nullable=True),
        sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_superadmin', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # --- brands_10dlc ---
    op.create_table(
        'brands_10dlc',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bandwidth_brand_id', sa.String(255), nullable=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('legal_name', sa.String(255), nullable=False),
        sa.Column('dba_name', sa.String(255), nullable=True),
        sa.Column('ein', sa.String(20), nullable=False),
        sa.Column('street', sa.String(255), nullable=False),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('state', sa.String(50), nullable=False),
        sa.Column('zip_code', sa.String(20), nullable=False),
        sa.Column('country', sa.String(2), nullable=False, server_default='US'),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('vertical', sa.String(100), nullable=False),
        sa.Column('stock_symbol', sa.String(10), nullable=True),
        sa.Column('stock_exchange', sa.String(20), nullable=True),
        sa.Column('trust_score', sa.Integer(), nullable=True),
        sa.Column('vetting_status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('registration_status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('email', sa.String(100), nullable=False),
        sa.Column('brand_relationship', sa.String(50), nullable=True),
        sa.Column('is_main', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('alt_business_id', sa.String(50), nullable=True),
        sa.Column('alt_business_id_type', sa.String(10), nullable=True),
        sa.Column('business_contact_email', sa.String(255), nullable=True),
        sa.Column('identity_status', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- campaigns_10dlc ---
    op.create_table(
        'campaigns_10dlc',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('brand_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bandwidth_campaign_id', sa.String(255), nullable=True),
        sa.Column('use_case', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('sample_messages', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('subscriber_optin', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('subscriber_optout', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('subscriber_help', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('number_pool', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('embedded_links', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('embedded_phone', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('age_gated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('message_flow', sa.Text(), nullable=False, server_default=''),
        sa.Column('help_message', sa.String(320), nullable=False, server_default='Reply HELP for help.'),
        sa.Column('help_keywords', sa.String(255), nullable=False, server_default='HELP'),
        sa.Column('optin_message', sa.String(320), nullable=True),
        sa.Column('optin_keywords', sa.String(255), nullable=True),
        sa.Column('optout_message', sa.String(320), nullable=False, server_default='You have been unsubscribed. Reply START to resubscribe.'),
        sa.Column('optout_keywords', sa.String(255), nullable=False, server_default='STOP'),
        sa.Column('direct_lending', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('affiliate_marketing', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('auto_renewal', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('sub_usecases', postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column('privacy_policy_link', sa.String(255), nullable=True),
        sa.Column('terms_and_conditions_link', sa.String(255), nullable=True),
        sa.Column('reference_id', sa.String(50), nullable=True),
        sa.Column('mps_limit', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('daily_limit', sa.Integer(), nullable=False, server_default='2000'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['brand_id'], ['brands_10dlc.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- dlc_applications ---
    op.create_table(
        'dlc_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_type', sa.String(20), nullable=False),
        sa.Column('brand_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('form_data', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
        sa.Column('submitted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('bandwidth_response', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['brand_id'], ['brands_10dlc.id']),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns_10dlc.id']),
        sa.ForeignKeyConstraint(['submitted_by'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_dlc_applications_tenant_id', 'dlc_applications', ['tenant_id'])

    # --- phone_numbers ---
    op.create_table(
        'phone_numbers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('number', sa.String(20), nullable=False),
        sa.Column('number_type', sa.String(20), nullable=False),
        sa.Column('bandwidth_order_id', sa.String(255), nullable=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('capabilities', postgresql.JSONB(), nullable=False, server_default='["sms"]'),
        sa.Column('monthly_cost', sa.Numeric(8, 4), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns_10dlc.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_phone_numbers_number', 'phone_numbers', ['number'])

    # --- contacts ---
    op.create_table(
        'contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phone_number', sa.String(20), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=True),
        sa.Column('last_name', sa.String(255), nullable=True),
        sa.Column('custom_fields', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('opted_in_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opted_out_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opt_in_method', sa.String(100), nullable=True),
        sa.Column('last_messaged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'phone_number', name='uq_contact_tenant_phone'),
    )
    op.create_index('ix_contacts_phone_number', 'contacts', ['phone_number'])

    # --- contact_lists ---
    op.create_table(
        'contact_lists',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('tag_color', sa.String(7), nullable=False, server_default='#3b82f6'),
        sa.Column('contact_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_smart', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('smart_filter', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- contact_list_members ---
    op.create_table(
        'contact_list_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('list_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.ForeignKeyConstraint(['list_id'], ['contact_lists.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contact_id', 'list_id', name='uq_contact_list_membership'),
    )

    # --- api_keys ---
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('key_prefix', sa.String(8), nullable=False),
        sa.Column('scopes', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'])

    # --- campaigns ---
    op.create_table(
        'campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('campaign_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('from_number_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('number_pool_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('message_template', sa.Text(), nullable=False),
        sa.Column('media_urls', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('target_list_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('exclude_list_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('segment_filter', postgresql.JSONB(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('send_window_start', sa.Time(), nullable=True),
        sa.Column('send_window_end', sa.Time(), nullable=True),
        sa.Column('send_window_timezone', sa.String(50), nullable=False, server_default='America/New_York'),
        sa.Column('throttle_mps', sa.Integer(), nullable=True),
        sa.Column('total_recipients', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sent_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('delivered_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('opted_out_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ab_variants', postgresql.JSONB(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['from_number_id'], ['phone_numbers.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- campaign_messages ---
    op.create_table(
        'campaign_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_number', sa.String(20), nullable=False),
        sa.Column('to_number', sa.String(20), nullable=False),
        sa.Column('message_body', sa.Text(), nullable=False),
        sa.Column('media_urls', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('bandwidth_message_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_description', sa.Text(), nullable=True),
        sa.Column('segments', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('cost', sa.Numeric(8, 6), nullable=False, server_default='0'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_campaign_messages_campaign_id', 'campaign_messages', ['campaign_id'])
    op.create_index('ix_campaign_messages_bandwidth_message_id', 'campaign_messages', ['bandwidth_message_id'])

    # --- conversations ---
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phone_number_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_phone', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('unread_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tags', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.ForeignKeyConstraint(['phone_number_id'], ['phone_numbers.id']),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- messages (inbox) ---
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('sender_type', sa.String(20), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('media_urls', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('bandwidth_message_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('segments', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('cost', sa.Numeric(8, 6), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])

    # --- auto_replies ---
    op.create_table(
        'auto_replies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phone_number_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('trigger_type', sa.String(20), nullable=False),
        sa.Column('trigger_value', sa.Text(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=False),
        sa.Column('media_urls', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['phone_number_id'], ['phone_numbers.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- ai_agents ---
    op.create_table(
        'ai_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('phone_number_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('model', sa.String(50), nullable=False, server_default='gpt-4o'),
        sa.Column('temperature', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('max_tokens', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('knowledge_base', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('escalation_rules', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('conversation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_response_time_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- ai_agent_logs ---
    op.create_table(
        'ai_agent_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('inbound_message', sa.Text(), nullable=False),
        sa.Column('ai_response', sa.Text(), nullable=False),
        sa.Column('model_used', sa.String(50), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('escalated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['ai_agents.id']),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- templates ---
    op.create_table(
        'templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('media_urls', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('is_shared', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- drip_sequences ---
    op.create_table(
        'drip_sequences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('trigger_event', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- drip_steps ---
    op.create_table(
        'drip_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('delay_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('message_template', sa.Text(), nullable=False),
        sa.Column('media_urls', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('condition', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['sequence_id'], ['drip_sequences.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- drip_enrollments ---
    op.create_table(
        'drip_enrollments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_step', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('next_step_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['sequence_id'], ['drip_sequences.id']),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- scheduled_messages ---
    op.create_table(
        'scheduled_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_number_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('media_urls', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.ForeignKeyConstraint(['from_number_id'], ['phone_numbers.id']),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- opt_out_logs ---
    op.create_table(
        'opt_out_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phone_number', sa.String(20), nullable=False),
        sa.Column('keyword_used', sa.String(50), nullable=False),
        sa.Column('bandwidth_message_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- webhook_logs ---
    op.create_table(
        'webhook_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('bandwidth_message_id', sa.String(255), nullable=True),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_webhook_logs_bandwidth_message_id', 'webhook_logs', ['bandwidth_message_id'])

    # --- billing_events ---
    op.create_table(
        'billing_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_cost', sa.Numeric(10, 6), nullable=False),
        sa.Column('total_cost', sa.Numeric(10, 4), nullable=False),
        sa.Column('stripe_invoice_item_id', sa.String(255), nullable=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- audit_logs ---
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('billing_events')
    op.drop_index('ix_webhook_logs_bandwidth_message_id', table_name='webhook_logs')
    op.drop_table('webhook_logs')
    op.drop_table('opt_out_logs')
    op.drop_table('scheduled_messages')
    op.drop_table('drip_enrollments')
    op.drop_table('drip_steps')
    op.drop_table('drip_sequences')
    op.drop_table('templates')
    op.drop_table('ai_agent_logs')
    op.drop_table('ai_agents')
    op.drop_table('auto_replies')
    op.drop_index('ix_messages_conversation_id', table_name='messages')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_index('ix_campaign_messages_bandwidth_message_id', table_name='campaign_messages')
    op.drop_index('ix_campaign_messages_campaign_id', table_name='campaign_messages')
    op.drop_table('campaign_messages')
    op.drop_table('campaigns')
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.drop_table('api_keys')
    op.drop_table('contact_list_members')
    op.drop_table('contact_lists')
    op.drop_index('ix_contacts_phone_number', table_name='contacts')
    op.drop_table('contacts')
    op.drop_index('ix_phone_numbers_number', table_name='phone_numbers')
    op.drop_table('phone_numbers')
    op.drop_table('campaigns_10dlc')
    op.drop_index('ix_dlc_applications_tenant_id', table_name='dlc_applications')
    op.drop_table('dlc_applications')
    op.drop_table('brands_10dlc')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    op.drop_table('tenants')
