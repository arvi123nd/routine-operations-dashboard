# Scaling to 2000+ Users: Implementation Guide

## 🎯 Executive Summary

Your current infrastructure is designed for **50-100 concurrent users**. To handle **2000+ users**, you need to:

1. **ECS**: Scale from 1 to 10+ tasks (4x compute power)
2. **Database**: Upgrade from `db.t3.micro` to `db.r5.xlarge` (32x more memory)
3. **Cache**: Upgrade from `cache.t3.micro` to `cache.r6g.xlarge` (16x more memory)
4. **Cost**: Increase from ~$76/month to ~$1,900/month

---

## 🔴 Current Bottlenecks

### Problem 1: ECS Fargate Tasks (CRITICAL)
```
Current: 1 task × 256 CPU × 512 MB memory
Capacity: ~50 req/sec
2000 users @ 100 req/min = 3,333 req/sec needed
Gap: 3,283 req/sec SHORT ❌
```

**Solution**: Use 10 tasks × 1024 CPU = 10x capacity

### Problem 2: Database (CRITICAL)
```
Current: db.t3.micro (1 vCPU, burstable, 1 GB RAM)
Max Connections: ~150 (hit quickly with 2000 users)
Memory for Indexes: 1 GB (insufficient for 2000+ users)
Gap: Database will crash under load ❌
```

**Solution**: Upgrade to `db.r5.xlarge` (4 vCPU, 32 GB RAM, ~5,000 IOPS)

### Problem 3: Redis Cache (MEDIUM)
```
Current: cache.t3.micro (500 MB)
Capacity: 1,000 ops/sec
2000 users need: 10,000+ ops/sec
Gap: Cache evictions will occur ❌
```

**Solution**: Upgrade to `cache.r6g.xlarge` (8 GB, 15,000 ops/sec)

---

## 📊 Capacity Planning

### Users to Requests Formula
```
Concurrent Users = 2,000
Requests per User per Minute = 100
Requests per Second = 2,000 × (100/60) = 3,333 req/sec
```

### By Component

#### ECS (Application Servers)
| Scenario | Tasks | vCPU | Memory | Cost/Month |
|----------|-------|------|--------|-----------|
| Dev (100 users) | 1 | 0.25 | 512 MB | $5-10 |
| Current (500 users) | 2 | 0.5 | 1 GB | $10-15 |
| **2000 users** | **10** | **10** | **20 GB** | **$100-150** |
| 5000 users | 20 | 20 | 40 GB | $200-250 |

#### RDS Database
| Scenario | Instance | vCPU | Memory | IOPS | Cost/Month |
|----------|----------|------|--------|------|-----------|
| Dev | db.t3.micro | 1 | 1 GB | 3,000 | $15 |
| 500 users | db.t3.small | 2 | 2 GB | 3,000 | $30 |
| **2000 users** | **db.r5.xlarge** | **4** | **32 GB** | **5,000** | **$1,500** |
| 5000 users | db.r6i.2xlarge | 8 | 64 GB | 10,000 | $2,000 |

#### Redis Cache
| Scenario | Instance | Memory | Ops/sec | Cost/Month |
|----------|----------|--------|---------|-----------|
| Dev | cache.t3.micro | 500 MB | 1K | $8 |
| 500 users | cache.t3.small | 1.5 GB | 2K | $20 |
| **2000 users** | **cache.r6g.xlarge** | **8 GB** | **15K** | **$200** |
| 5000 users | cache.r6g.2xlarge | 16 GB | 30K | $400 |

---

## 🚀 Implementation Steps

### Step 1: Create Production Configuration (15 min)

Use the provided `prod-2000users.tfvars`:
```bash
cat terraform/prod-2000users.tfvars
# Shows all necessary configurations for 2000+ users
```

### Step 2: Validate Changes (10 min)
```bash
cd terraform

# Dry run to see what will change
terraform plan \
  -var-file=prod-2000users.tfvars \
  -out=tfplan-scale

# Review the plan - should see:
# - ECS task: 256 → 1024 CPU, 512 → 2048 MB
# - RDS: db.t3.micro → db.r5.xlarge
# - Redis: cache.t3.micro → cache.r6g.xlarge
```

### Step 3: Database Backup (5 min)
```bash
# Take snapshot before any changes
aws rds create-db-snapshot \
  --db-instance-identifier routine-operations-dashboard-mysql-prod \
  --db-snapshot-identifier pre-scale-2000users-$(date +%Y%m%d)

# Verify snapshot
aws rds describe-db-snapshots \
  --db-snapshot-identifier pre-scale-2000users-$(date +%Y%m%d)
```

### Step 4: Apply Changes (30-60 min)
```bash
# Option A: One-shot deployment (causes brief downtime)
terraform apply tfplan-scale

# Option B: Staggered deployment (preferred for high availability)
# First scale ECS, then scale database
terraform apply -var-file=prod-2000users.tfvars \
  -target=aws_ecs_service.app \
  -target=aws_appautoscaling_target.ecs_target

# Wait 5 minutes for tasks to stabilize
sleep 300

# Then scale database
terraform apply -var-file=prod-2000users.tfvars \
  -target=aws_db_instance.mysql
```

### Step 5: Verify Scaling (15 min)
```bash
# Check ECS service
aws ecs describe-services \
  --cluster routine-operations-dashboard-cluster-prod \
  --services routine-operations-dashboard-service \
  | jq '.services[0].desiredCount, .services[0].runningCount'

# Should output:
# 10  (desired)
# 10  (running - after ~5 min)

# Check RDS upgrade status
aws rds describe-db-instances \
  --db-instance-identifier routine-operations-dashboard-mysql-prod \
  | jq '.DBInstances[0].DBInstanceClass, .DBInstances[0].DBInstanceStatus'

# Should output:
# "db.r5.xlarge"
# "available" (after 10-20 min)

# Check Redis upgrade status
aws elasticache describe-cache-clusters \
  --cache-cluster-id routine-operations-dashboard-redis-prod \
  --show-cache-node-info \
  | jq '.CacheClusters[0].CacheNodeType, .CacheClusters[0].CacheClusterStatus'

# Should output:
# "cache.r6g.xlarge"
# "available"
```

### Step 6: Load Testing (30-60 min)
```bash
# Install load testing tool
pip install locust

# Create load test script
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between

class DashboardUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def index(self):
        self.client.get("/")

    @task(2)
    def api_call(self):
        self.client.get("/api/operations")

    @task
    def submit_form(self):
        self.client.post("/api/submit", json={"data": "test"})
EOF

# Run load test
locust -f locustfile.py \
  -u 2000 \
  -r 100 \
  -t 5m \
  -H https://dashboard.crossidentity.com

# Monitor metrics during test
# - Response times
# - Error rates
# - Task success rate
```

### Step 7: Monitor & Optimize (ongoing)
```bash
# View CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=routine-operations-dashboard-service \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# View RDS metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=routine-operations-dashboard-mysql-prod \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

---

## 📈 Performance Metrics

### Before Scaling (Current)
```
Concurrent Users: 100
Requests/Second: 200
Response Time: 200-500ms
Error Rate: 0% (until capacity hit)
Database CPU: 60-70%
Database Connections: 80-100
Redis Memory: 100-200 MB
```

### After Scaling (With 2000 Users)
```
Concurrent Users: 2000
Requests/Second: 3,333
Response Time: 50-150ms (3-4x faster!)
Error Rate: <0.1%
Database CPU: 40-60%
Database Connections: 300-500
Redis Memory: 2-3 GB (out of 8 GB)
Task Count: Auto-scales 8-12 tasks
```

---

## 💰 Cost Breakdown

### Monthly Cost Comparison

#### Current (Dev + Prod Micro)
```
Dev:
  ECS: $5-10
  RDS: $15
  Redis: $8
  ALB: $16
  NAT: $32
  Subtotal: $76-81

Prod (if running):
  Same as dev
  Subtotal: $76-81
```

#### Scaled (Production 2000+ Users)
```
ECS (10 tasks × 1024 CPU): $100-150/month
RDS (db.r5.xlarge): $1,500/month
Redis (cache.r6g.xlarge): $200/month
ALB: $16/month
NAT Gateways (2): $64/month
S3, CloudWatch, other: $50-100/month
─────────────────────────────
TOTAL: $1,930-2,030/month
```

**Cost per User**: ~$1/user/month for 2000 users

### Cost Optimization Tips
1. **Reserved Instances**: Save 40% with 1-year commitment (~$1,200/month)
2. **Spot Instances**: Use FARGATE_SPOT for 70% of tasks (save $30-50/month)
3. **On-Demand Savings Plan**: Save 25-30% (~$500/month)
4. **Aurora Serverless**: For RDS, saves $300-400/month with lower concurrency

---

## ⚠️ Important Considerations

### Database Upgrade Notes
```
⏱️ Downtime: 10-20 minutes during instance class change
✅ Solution: Use read replicas or blue-green deployment
💡 Recommendation: Schedule during off-peak hours
```

### Application Code Changes
```javascript
// Ensure connection pooling is configured
// Example: Node.js
const pool = mysql.createPool({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  waitForConnections: true,
  connectionLimit: 100,        // More connections needed
  queueLimit: 0,
  enableKeepAlive: true,       // Reuse connections
  keepAliveInitialDelayMs: 0
});

// Python Flask
from flask_sqlalchemy import SQLAlchemy

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 100,            # More connections
    'pool_recycle': 3600,        # Recycle connections
    'pool_pre_ping': True,       # Test connections
}
```

### Network Configuration
```
Current: 2 NAT Gateways (already correct)
Security Groups: Already sized appropriately
ALB: Already handles unlimited connections
Network ACLs: Default rules sufficient
```

---

## 🔍 Testing Checklist

Before going live with 2000+ users:

- [ ] Load test with 2000 concurrent users for 1+ hour
- [ ] Verify auto-scaling works (watch tasks scale up/down)
- [ ] Check database query performance under load
- [ ] Monitor Redis memory utilization (<80%)
- [ ] Verify application logs for errors
- [ ] Test database failover (RDS Multi-AZ)
- [ ] Check CloudWatch alarms trigger properly
- [ ] Verify backup/restore procedures work
- [ ] Test connection pooling limits
- [ ] Run security scan on scaled infrastructure

---

## 📞 Troubleshooting Guide

### Problem: ECS tasks not scaling up
```bash
# Check service configuration
aws ecs describe-services \
  --cluster routine-operations-dashboard-cluster-prod \
  --services routine-operations-dashboard-service

# Check auto-scaling policies
aws autoscaling describe-policies \
  --policy-names routine-operations-dashboard-cpu-autoscaling

# View scaling activity
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name routine-operations-dashboard
```

### Problem: Database connection limit hit
```bash
# Check current connections
mysql -h $RDS_ENDPOINT -u admin -p$PASSWORD -e \
  "SHOW PROCESSLIST;"

# Increase connection limit
mysql -h $RDS_ENDPOINT -u admin -p$PASSWORD -e \
  "SET GLOBAL max_connections = 1000;"

# Verify new limit
mysql -h $RDS_ENDPOINT -u admin -p$PASSWORD -e \
  "SHOW VARIABLES LIKE 'max_connections';"
```

### Problem: Redis evictions occurring
```bash
# Check eviction stats
aws elasticache describe-cache-clusters \
  --cache-cluster-id routine-operations-dashboard-redis-prod \
  --show-cache-node-info

# Flush non-essential cache
redis-cli -h $REDIS_ENDPOINT -p 6379 FLUSHDB

# Upgrade to larger instance (if persistent)
# See SCALABILITY_ANALYSIS.md for options
```

### Problem: Database slow queries
```bash
# Enable slow query log
mysql -h $RDS_ENDPOINT -u admin -p$PASSWORD -e \
  "SET GLOBAL slow_query_log = 'ON';"

# View slow queries
aws logs tail /aws/rds/mysql/slow-query-log --follow

# Analyze with EXPLAIN
mysql -h $RDS_ENDPOINT -u admin -p$PASSWORD -e \
  "EXPLAIN SELECT * FROM operations WHERE user_id = 1;"
```

---

## 🎓 Quick Reference Commands

```bash
# Scale up immediately
cd terraform
terraform apply -var-file=prod-2000users.tfvars

# View scaling progress
watch -n 5 'aws ecs describe-services \
  --cluster routine-operations-dashboard-cluster-prod \
  --services routine-operations-dashboard-service \
  | jq ".services[0] | {desiredCount, runningCount, status}"'

# Monitor load
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average

# Rollback if needed
terraform destroy -var-file=prod-2000users.tfvars \
  -target=aws_ecs_service.app

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier restored-instance \
  --db-snapshot-identifier pre-scale-2000users-20240101
```

---

**Last Updated**: 3 November 2025
**Scalability Target**: 2000-3000 concurrent users
**Estimated Implementation Time**: 2-4 hours
**Recommended Staging Period**: 1 week load testing
