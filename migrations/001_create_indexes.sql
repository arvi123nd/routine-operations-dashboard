-- ================================================================
-- Database Optimization Indexes
-- RUN THESE BEFORE DEPLOYING TO PRODUCTION
-- ================================================================

-- These indexes will dramatically improve query performance
-- Expected improvement: 10x-100x faster queries

-- ================================================================
-- LOGIN TABLE INDEXES
-- ================================================================

-- Primary index for filtering by tenant, subtenant, and date
-- Covers most common query pattern
-- Time Complexity: O(n) → O(log n + m)
CREATE INDEX IF NOT EXISTS idx_login_tenant_time 
ON idx2_audit_login(tenant, subtenant, timestamp, status);

-- Index for user-specific queries
CREATE INDEX IF NOT EXISTS idx_login_user 
ON idx2_audit_login(user, timestamp);

-- Index for IP-based queries (for Access Map)
CREATE INDEX IF NOT EXISTS idx_login_ip 
ON idx2_audit_login(ip, timestamp) 
WHERE ip IS NOT NULL AND ip != '';

-- Covering index for count queries (includes status in index)
CREATE INDEX IF NOT EXISTS idx_login_status_time 
ON idx2_audit_login(tenant, subtenant, status, timestamp);

-- ================================================================
-- PASSWORD RESET TABLE INDEXES
-- ================================================================

-- Primary index for password reset queries
CREATE INDEX IF NOT EXISTS idx_password_tenant_time 
ON idx2_audit_fgtpwd(tenant, subtenant, timestamp, status);

-- Index for user-specific password reset queries
CREATE INDEX IF NOT EXISTS idx_password_user 
ON idx2_audit_fgtpwd(user, timestamp);

-- ================================================================
-- SSO TABLE INDEXES
-- ================================================================

-- Primary index for SSO queries
CREATE INDEX IF NOT EXISTS idx_sso_tenant_time 
ON idx2_audit_sso(tenant, subtenant, timestamp);

-- Index for user activity queries
CREATE INDEX IF NOT EXISTS idx_sso_user 
ON idx2_audit_sso(user, timestamp);

-- Index for app-specific queries
CREATE INDEX IF NOT EXISTS idx_sso_app 
ON idx2_audit_sso(app, timestamp);

-- Covering index for user-app combinations
CREATE INDEX IF NOT EXISTS idx_sso_user_app 
ON idx2_audit_sso(user, app, timestamp);

-- ================================================================
-- VERIFICATION QUERIES
-- ================================================================

-- Run these to verify indexes are created
SHOW INDEX FROM idx2_audit_login;
SHOW INDEX FROM idx2_audit_fgtpwd;
SHOW INDEX FROM idx2_audit_sso;

-- ================================================================
-- PERFORMANCE TESTING
-- ================================================================

-- Test query performance before and after indexes
-- Should show significant improvement in execution time

-- Login metrics query (should use idx_login_tenant_time)
EXPLAIN SELECT 
    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as fail_count
FROM idx2_audit_login
WHERE tenant = 22 
  AND subtenant = 13
  AND DATE(timestamp) BETWEEN '2025-10-17' AND '2025-10-24';

-- SSO metrics query (should use idx_sso_tenant_time)
EXPLAIN SELECT 
    COUNT(DISTINCT user) as unique_users,
    COUNT(DISTINCT app) as unique_apps,
    COUNT(*) as total_sessions
FROM idx2_audit_sso
WHERE tenant = 22 
  AND subtenant = 13
  AND DATE(timestamp) BETWEEN '2025-10-17' AND '2025-10-24';

-- ================================================================
-- MAINTENANCE
-- ================================================================

-- Analyze tables after creating indexes for optimal query plans
ANALYZE TABLE idx2_audit_login;
ANALYZE TABLE idx2_audit_fgtpwd;
ANALYZE TABLE idx2_audit_sso;

-- ================================================================
-- NOTES
-- ================================================================

/*
INDEX NAMING CONVENTION:
- idx_[table]_[columns]

EXPECTED IMPROVEMENTS:
- Without indexes: O(n) - full table scan
- With indexes: O(log n + m) - index seek + matched rows

EXAMPLE IMPROVEMENTS:
- 1M rows table without index: ~2-5 seconds
- 1M rows table with index: ~50-200ms
- Improvement: 10x-100x faster!

DISK SPACE:
- Each index adds ~10-30% of table size
- For 1GB table: expect 100-300MB additional space
- Trade-off: Disk space for query speed (WORTH IT!)

MAINTENANCE:
- Indexes auto-update on INSERT/UPDATE/DELETE
- Slight performance impact on writes (~5-10%)
- Huge performance gain on reads (~1000%+)
- For read-heavy dashboard: ESSENTIAL!
*/
