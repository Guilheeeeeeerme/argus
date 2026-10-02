# Account memberships

Public signup is disabled for the MVP. Platform administrators create accounts and assign zero or more accounts in the Users panel. A user has one global role; membership grants account access without changing that role. Platform root/admin roles retain access to all accounts.

`account_user_memberships (user_id, account_id)` is authoritative for manager/operator access. The nullable `account_users.account_id` remains a compatibility/default-account field. Admin account create/update accepts `account_ids: []` to remove all memberships, or a list of account UUIDs to replace memberships. Legacy `account_id` writes replace the list with that single account (or none for null). Account responses include both fields.

`GET /v1/auth/accounts` lists selectable accounts. `PATCH /v1/auth/context` accepts an assigned `accountId`, or explicit null to clear selection. Selecting another account clears the unit. HTTP requests recheck active membership; revoked contexts are cleared in Redis and cannot access the former account's resources. WebSocket handshakes and event delivery also verify membership and current session account.

Migration 012 backfills existing primary assignments, enables RLS on memberships, and changes primary-account deletion to SET NULL so deleting one account does not delete a shared user. Deploy the migration before the new application. For an application rollback, retain the additive schema: old code can still use the primary account. A schema downgrade drops extra memberships and should only run after exporting them and reconciling accounts to single-account access. Do not run old and new account-management writers concurrently: legacy code does not update membership rows.
