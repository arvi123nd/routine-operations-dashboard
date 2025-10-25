#!/bin/bash
# ================================================================
# Database Backup Script
# ================================================================

set -e

# Load environment
if [ -f .env ]; then
    source .env
fi

# Configuration
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="dashboard_backup_${DATE}.sql.gz"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

# Create backup directory
mkdir -p $BACKUP_DIR

echo "🔄 Starting database backup..."

# Backup database
docker-compose exec -T mysql mysqldump \
    -u${DB_USER} \
    -p${DB_PASSWORD} \
    ${DB_NAME} \
    --single-transaction \
    --quick \
    --lock-tables=false \
    | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "✅ Backup created: ${BACKUP_FILE}"
    echo "📦 Size: $(du -h ${BACKUP_DIR}/${BACKUP_FILE} | cut -f1)"
else
    echo "❌ Backup failed"
    exit 1
fi

# Remove old backups
echo "🧹 Cleaning old backups (older than ${RETENTION_DAYS} days)..."
find $BACKUP_DIR -name "dashboard_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "✅ Backup complete!"
