#!/bin/bash

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$TIMESTAMP"

echo "💾 Creating backup: $BACKUP_DIR"

mkdir -p "$BACKUP_DIR"

# Backup Qdrant data
echo "Backing up Qdrant..."
docker-compose exec qdrant qdrant snapshot --host http://localhost:6333 cob_knowledge_base
docker cp $(docker-compose ps -q qdrant):/qdrant/snapshots "$BACKUP_DIR/qdrant"

# Backup Redis data
echo "Backing up Redis..."
docker-compose exec redis redis-cli --rdb /data/dump.rdb
docker cp $(docker-compose ps -q redis):/data/dump.rdb "$BACKUP_DIR/redis"

# Backup logs
echo "Backing up logs..."
cp -r logs "$BACKUP_DIR/"

# Backup configuration
echo "Backing up configuration..."
cp .env "$BACKUP_DIR/"
cp docker-compose.yml "$BACKUP_DIR/"

# Create archive
tar -czf "backups/backup_$TIMESTAMP.tar.gz" -C "$BACKUP_DIR" .

echo "✅ Backup completed: backups/backup_$TIMESTAMP.tar.gz"
echo "Size: $(du -h backups/backup_$TIMESTAMP.tar.gz | cut -f1)"