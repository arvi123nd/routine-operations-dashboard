# Scaling Monitoring & Performance Metrics

## 📊 Key Metrics for 2000+ Users

### 1. Application Tier Metrics (ECS)

#### CPU Utilization
```
Current (1 task):    60-70% under baseline load
After Scaling (10 tasks): 40-50% under baseline load
Target Range:        30-70% (green zone)
Alert Threshold:     >85% (red zone)
Action:              Auto-scale if >70% for 2+ minutes
```

#### Memory Utilization
```
Current:   350-450 MB / 512 MB (70-90% full)
Scaled:    900-1200 MB / 2048 MB (45-60% utilization)
Target:    <75%
Alert:     >85% memory utilization
```

#### Task Count
```
Dev:       1-3 tasks
Scaled:    8-15 tasks (auto-scales 8-20)
Headroom:  Always maintain 2-3 extra capacity

Scaling Rules:
- Scale UP:   CPU >70% for 2 minutes OR Memory >80% for 2 minutes
- Scale DOWN: CPU <30% for 5 minutes AND Memory <60% for 5 minutes
```

#### Request Metrics
```
Requests/Second Target:    3,000-5,000 req/sec
Response Time p50:         50-100 ms
Response Time p95:         100-200 ms
Response Time p99:         200-500 ms
Error Rate Target:         <0.1%
```

---

### 2. Database Tier Metrics (RDS)

#### Connection Count
```
Current (db.t3.micro):     80-120 connections (limit ~150)
Scaled (db.r5.xlarge):     300-500 connections (limit ~1000)
Target Utilization:        <60% of max connections
Alert Threshold:           >700 connections
```

**Formula**: Connections = (ECS Tasks × App Thread Pool)
```
Before: 1 task × 50 pool = 50 connections
After:  10 tasks × 50 pool = 500 connections
```

#### Query Performance
```
SELECT query response:     10-50 ms
INSERT/UPDATE response:    20-100 ms
Complex JOIN response:     50-200 ms
Index scan response:       5-20 ms

Alert if p95 latency > 500 ms for 5 consecutive minutes
```

#### Storage I/O
```
Current (gp2, 3000 IOPS):
  Read: 1000-2000 IOPS
  Write: 500-1000 IOPS

Scaled (gp3, 5000 IOPS):
  Read: 2000-4000 IOPS
  Write: 1000-2000 IOPS

Target: <80% of provisioned IOPS
Alert: >90% of IOPS consumed
```

#### Backup & Replication Lag
```
Backup Duration:      5-10 minutes (should be quick)
Multi-AZ Replication Lag: <100 ms
Alert if lag > 1000 ms (indicates strain)
```

---

### 3. Cache Layer Metrics (Redis)

#### Memory Utilization
```
Current (cache.t3.micro, 500 MB):
  Usage: 400-450 MB (80-90% full)
  Eviction Rate: High (problematic)

Scaled (cache.r6g.xlarge, 8 GB):
  Usage: 2-4 GB (25-50% full)
  Eviction Rate: 0-10/sec (acceptable)

Target: <75% memory utilization
Alert: >85% OR evictions >100/sec
```

#### Operations Per Second
```
Current Capacity:    1,000 ops/sec
Scaled Capacity:     15,000 ops/sec
Target Usage:        <70% capacity
Alert Threshold:     >10,000 ops/sec
```

#### Hit Rate
```
Target Hit Rate:     >80% (cache working well)
Alert if <60% (indicates undersizing or invalidation issues)

Formula: Hit Rate = Hits / (Hits + Misses) × 100
- 85% hit rate = 85% of requests served from cache
- Saves database load significantly
```

#### Network Throughput
```
Current:   1-5 Mbps
Scaled:    10-20 Mbps
Max Capacity: 10 Gbps network
No concerns for typical usage
```

---

### 4. Load Balancer Metrics (ALB)

#### Connection Count
```
New Connections/sec:     1,000-5,000 conn/sec
Active Connections:      500-2,000
Request Count:           3,000-5,000 req/sec
Response Time:           50-200 ms
HTTP Error Rate:         <0.1%
```

#### Target Health
```
Healthy Targets:  10/10 (all running)
Unhealthy Targets: 0
Target Response Time: <500 ms for 99th percentile
```

---

### 5. Network & Throughput

#### Data Transfer
```
Inbound:  500 Mbps - 5 Gbps (test dependent)
Outbound: 100 Mbps - 500 Mbps
ALB Capacity: Can handle 10+ Gbps

Current Limit: Network bandwidth is NOT a bottleneck
```

#### Latency
```
ALB → ECS:    <10 ms
ECS → RDS:    5-15 ms (same AZ)
ECS → Redis:  5-15 ms (same AZ)
Total Path:   50-100 ms (acceptable)
```

---

## 📈 Monitoring Dashboards

### CloudWatch Dashboard Example
```hcl
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "routine-operations-prod"

  dashboard_body = jsonencode({
    widgets = [
      # ECS Metrics
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", { stat = "Average", label = "ECS CPU" }],
            ["AWS/ECS", "MemoryUtilization", { stat = "Average", label = "ECS Memory" }]
          ]
          period = 300
          stat   = "Average"
          region = "us-east-1"
        }
      },
      # Database Metrics
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "DatabaseConnections", { stat = "Average" }],
            ["AWS/RDS", "CPUUtilization", { stat = "Average" }],
            ["AWS/RDS", "ReadLatency", { stat = "Average" }]
          ]
          period = 300
          region = "us-east-1"
        }
      },
      # Redis Metrics
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ElastiCache", "DatabaseMemoryUsagePercentage", { stat = "Average" }],
            ["AWS/ElastiCache", "CacheHits", { stat = "Sum" }],
            ["AWS/ElastiCache", "Evictions", { stat = "Sum" }]
          ]
          period = 300
          region = "us-east-1"
        }
      }
    ]
  })
}
```

---

## 🚨 Critical Alerts

### Alert 1: High Database Connections
```bash
Metric:    DatabaseConnections > 700
Duration:  2 minutes
Action:    Page on-call engineer
```

### Alert 2: High Error Rate
```bash
Metric:    HTTPError Rate > 1%
Duration:  1 minute
Action:    Page on-call engineer
```

### Alert 3: Database Replication Lag
```bash
Metric:    ReplicationLag > 1000 ms
Duration:  1 minute
Action:    Investigate Multi-AZ failover
```

### Alert 4: Redis Evictions
```bash
Metric:    Evictions > 100/sec
Duration:  2 minutes
Action:    Increase cache size or reduce TTL
```

### Alert 5: ECS Task Failures
```bash
Metric:    Task Count < Desired Count
Duration:  1 minute
Action:    Check CloudWatch logs immediately
```

---

## 📊 Load Test Simulation

### Recommended Load Test Scenarios

#### Scenario 1: Steady Load (Baseline)
```
Users:            500 (ramp up over 5 minutes)
Duration:         30 minutes
Request Pattern:  Normal workflow
Expected:         CPU 30-50%, Connections 100-200
```

#### Scenario 2: Peak Load (2000 Users)
```
Users:            2000 (ramp up over 10 minutes)
Duration:         1 hour
Request Pattern:  Mixed (reads 70%, writes 30%)
Expected:         CPU 60-75%, Connections 300-500
                  Database: 15,000+ IOPS
                  Redis: 10,000+ ops/sec
```

#### Scenario 3: Spike Test (Sudden Traffic)
```
Users:            1000 → 5000 in 30 seconds
Duration:         20 minutes
Request Pattern:  Bursty
Expected:         Auto-scale kicks in within 2 minutes
                  Response time increases 2-3x briefly
                  Then normalizes as tasks spawn
```

#### Scenario 4: Sustained Load
```
Users:            2000 constant
Duration:         4 hours
Request Pattern:  Realistic usage
Goal:             Find memory leaks, connection issues
Expected:         Stable metrics throughout
```

---

## 📋 Performance Validation Checklist

After scaling to 2000+ users:

### Application Performance
- [ ] Response time p95 < 200 ms
- [ ] Response time p99 < 500 ms
- [ ] Error rate < 0.1%
- [ ] Throughput > 3,000 req/sec
- [ ] No memory leaks (memory stable over 4 hours)

### Database Performance
- [ ] Query latency p95 < 200 ms
- [ ] Connection count < 700
- [ ] Disk I/O utilization < 80%
- [ ] Multi-AZ lag < 100 ms
- [ ] Backup completes in < 10 min

### Cache Performance
- [ ] Cache hit rate > 80%
- [ ] Evictions < 10/sec
- [ ] Memory utilization < 75%
- [ ] Operation latency < 5 ms

### Scaling Performance
- [ ] Auto-scale UP occurs in < 2 minutes when CPU > 70%
- [ ] Auto-scale DOWN occurs in < 5 minutes when CPU < 30%
- [ ] No request failures during scaling
- [ ] New tasks become healthy within 60 seconds

### Infrastructure Stability
- [ ] All 10 ECS tasks remain healthy
- [ ] Zero database failovers
- [ ] Zero connection drops
- [ ] CloudWatch metrics continuous (no gaps)

---

## 📉 Performance Degradation Indicators

### Red Flags (Investigate Immediately)
1. **Response Time Increasing**: Could indicate database saturation
2. **Connection Limit Approaching**: Need connection pooling tuning
3. **High Error Rate**: Check application logs for issues
4. **Memory Growing**: Possible memory leak
5. **Cache Evictions Rising**: Cache undersized

### Optimization Opportunities
1. **CPU at 80%+**: Scale to more/larger tasks
2. **Database at 4 vCPU limit**: Consider read replicas
3. **Redis memory at 80%+**: Increase cache size
4. **P99 latency >500ms**: Profile slow queries

---

## 🔄 Continuous Monitoring Strategy

### Hourly Checks
```bash
# Check dashboard health
aws cloudwatch get-dashboard --dashboard-name routine-operations-prod

# Verify all services running
aws ecs describe-services \
  --cluster routine-operations-dashboard-cluster-prod \
  --services routine-operations-dashboard-service

# Quick performance check
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

### Daily Checks
- [ ] Review CloudWatch dashboard
- [ ] Check for any alarms triggered
- [ ] Verify backup completion
- [ ] Review error logs
- [ ] Monitor cost trends

### Weekly Checks
- [ ] Analyze performance trends
- [ ] Review slow query logs
- [ ] Check for inefficient cache usage
- [ ] Plan any optimization work
- [ ] Review cost forecast

### Monthly Checks
- [ ] Disaster recovery test
- [ ] Backup restore verification
- [ ] Performance baseline update
- [ ] Capacity planning review
- [ ] Cost optimization opportunities

---

**Last Updated**: 3 November 2025
**Target Scale**: 2000-3000 concurrent users
**Review Frequency**: Weekly (more often during first month)
