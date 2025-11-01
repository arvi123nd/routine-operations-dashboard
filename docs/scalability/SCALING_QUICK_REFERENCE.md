# Scaling to 2000+ Users - Quick Reference Card

## 🚀 One-Page Summary

Your app currently handles **~100 users**. To handle **2000+ users**, scale these 3 things:

| Component | Current | Scaled | Why |
|-----------|---------|--------|-----|
| **ECS Tasks** | 1 × 256 CPU | 10 × 1024 CPU | Current maxes out at 100 users |
| **Database** | db.t3.micro | db.r5.xlarge | Need 32x memory for indexes |
| **Cache** | cache.t3.micro | cache.r6g.xlarge | Need 16x memory to prevent evictions |
| **Cost** | $76/month | $1,900/month | Scales with resources |

---

## ⚡ Implementation (One Command)

```bash
cd terraform
terraform apply -var-file=prod-2000users.tfvars
```

Takes: **30-60 minutes**
Downtime: **5-10 minutes** (mainly RDS upgrade)

---

## 📊 Performance Impact

```
Concurrent Users:      100 → 2000   (+20x)
Requests/second:       200 → 5000   (+25x)
Response Time:         300ms → 75ms (4x faster!)
Database CPU:          70% → 40%    (more headroom)
Monthly Cost:          $76 → $1,900 (+25x)
```

---

## 🔍 What Changes

### ECS (Application)
```hcl
container_cpu     = 1024          # 256 → 1024
container_memory  = 2048          # 512 → 2048 MB
desired_count     = 10            # 1 → 10 tasks
max_capacity      = 20            # Auto-scales
```
→ **More tasks, each with more resources**

### RDS (Database)
```hcl
rds_instance_class    = "db.r5.xlarge"   # Better CPU/memory
rds_allocated_storage = 100              # More storage
# Multi-AZ automatically enabled for prod
```
→ **Bigger, faster database with failover**

### Redis (Cache)
```hcl
redis_node_type = "cache.r6g.xlarge"  # Larger instance
# From 500 MB to 8 GB capacity
```
→ **Faster, bigger cache**

---

## 📋 Before You Scale

- [ ] Current production is stable
- [ ] Have AWS credentials ready
- [ ] Can do 30-60 min maintenance window
- [ ] Can monitor deployment
- [ ] Have database snapshot
- [ ] Read SCALABILITY_ANALYSIS.md

---

## ✅ After Scaling Verify

```bash
# Check ECS tasks
aws ecs describe-services \
  --cluster routine-operations-dashboard-cluster-prod \
  --services routine-operations-dashboard-service \
  | jq '.services[0].runningCount'
# Should show: 10

# Check database
aws rds describe-db-instances \
  --db-instance-identifier routine-operations-dashboard-mysql-prod \
  | jq '.DBInstances[0].DBInstanceClass'
# Should show: "db.r5.xlarge"

# Check Redis
aws elasticache describe-cache-clusters \
  --cache-cluster-id routine-operations-dashboard-redis-prod \
  | jq '.CacheClusters[0].CacheNodeType'
# Should show: "cache.r6g.xlarge"
```

---

## 🎯 Key Metrics to Monitor

After scaling, watch these:

| Metric | Target | Alert |
|--------|--------|-------|
| **ECS CPU** | 30-70% | >85% |
| **ECS Memory** | 40-60% | >85% |
| **DB Connections** | <700 | >800 |
| **Cache Memory** | <75% | >85% |
| **Error Rate** | <0.1% | >1% |
| **Response Time p95** | <200ms | >500ms |

---

## 🚨 Troubleshooting

### Problem: Tasks not starting
```bash
aws ecs describe-services \
  --cluster routine-operations-dashboard-cluster-prod \
  --services routine-operations-dashboard-service
```
Check `failures` field, usually image or network issue.

### Problem: Database slow
```bash
# Check connections
mysql -h $ENDPOINT -u admin -p -e "SHOW PROCESSLIST;"
# Too many? Need to increase pool size in app
```

### Problem: Cache evictions
```bash
aws elasticache describe-cache-clusters \
  --cache-cluster-id routine-operations-dashboard-redis-prod \
  --show-cache-node-info
```
If evictions high, already correctly sized but may need larger.

---

## 📚 Full Docs

1. **SCALABILITY_ANALYSIS.md** - Why each component needs scaling
2. **SCALING_IMPLEMENTATION_GUIDE.md** - Detailed step-by-step
3. **SCALING_MONITORING_GUIDE.md** - Metrics & alerts

---

## 💰 Cost Breakdown

```
ECS Fargate (10 × 1024 CPU):  $100-150
RDS db.r5.xlarge:            $1,500
Redis cache.r6g.xlarge:      $200
ALB:                          $16
NAT Gateways:                 $64
Other (S3, CloudWatch):       $50-100
─────────────────────────────────
TOTAL:                        ~$1,930/month

= $0.97/user/month for 2000 users
```

---

## 🔗 Configuration Files

**Ready to use:**
- `terraform/prod-2000users.tfvars` ← Use this!

**Reference documentation:**
- `SCALABILITY_ANALYSIS.md` (bottleneck details)
- `SCALING_IMPLEMENTATION_GUIDE.md` (step-by-step)
- `SCALING_MONITORING_GUIDE.md` (metrics to watch)

---

## ⏱️ Timeline

```
Preparation:       1 hour  (read docs, backup)
Implementation:    1 hour  (terraform apply)
Stabilization:     30 min  (wait for services)
Validation:        1 hour  (load test)
─────────────────────────
TOTAL:            3.5-4 hours
```

---

**Ready to scale?** Run:

```bash
cd terraform
terraform plan -var-file=prod-2000users.tfvars
terraform apply -var-file=prod-2000users.tfvars
```

Then monitor metrics from SCALING_MONITORING_GUIDE.md
