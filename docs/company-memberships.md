# Company memberships

Public signup is disabled for the MVP. Platform administrators create accounts and assign zero or more companies in the Users panel. A user has one global role; membership grants company access without changing that role. Platform root/admin roles retain access to all companies.

`company_user_memberships (user_id, company_id)` is authoritative for manager/operator access. The nullable `company_users.company_id` remains a compatibility/default-company field. Admin account create/update accepts `company_ids: []` to remove all memberships, or a list of company UUIDs to replace memberships. Legacy `company_id` writes replace the list with that single company (or none for null). Account responses include both fields.

`GET /v1/auth/companies` lists selectable companies. `PATCH /v1/auth/context` accepts an assigned `companyId`, or explicit null to clear selection. Selecting another company clears the establishment. HTTP requests recheck active membership; revoked contexts are cleared in Redis and cannot access the former company's resources. WebSocket handshakes and event delivery also verify membership and current session company.

Migration 012 backfills existing primary assignments, enables RLS on memberships, and changes primary-company deletion to SET NULL so deleting one company does not delete a shared user. Deploy the migration before the new application. For an application rollback, retain the additive schema: old code can still use the primary company. A schema downgrade drops extra memberships and should only run after exporting them and reconciling accounts to single-company access. Do not run old and new account-management writers concurrently: legacy code does not update membership rows.
