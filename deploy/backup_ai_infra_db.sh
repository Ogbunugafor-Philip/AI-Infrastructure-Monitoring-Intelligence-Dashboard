#!/bin/bash
set -euo pipefail
ENV_FILE=/root/projects/AI_Infra_Monitoring/.env
BACKUP_DIR=/root/backups/ai_infra_db
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME=ai_infra_db
BACKUP_FILE=$BACKUP_DIR/backup_$DATE.sql.gz
ENCRYPTED_FILE=$BACKUP_FILE.enc

# Load secrets from .env (DB auth for pg_dump + backup encryption key).
DB_BACKUP_ENCRYPTION_KEY=$(grep -E '^DB_BACKUP_ENCRYPTION_KEY=' "$ENV_FILE" | cut -d= -f2-)
export PGPASSWORD=$(grep -E '^DATABASE_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)

mkdir -p $BACKUP_DIR
pg_dump -U ai_infra_admin -h localhost $DB_NAME | gzip > $BACKUP_FILE
openssl enc -aes-256-cbc -pbkdf2 -in $BACKUP_FILE -out $ENCRYPTED_FILE -k "$DB_BACKUP_ENCRYPTION_KEY"
rm $BACKUP_FILE
find $BACKUP_DIR -name "*.enc" -mtime +7 -delete
echo "Backup completed: $ENCRYPTED_FILE"
