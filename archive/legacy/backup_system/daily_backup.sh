#!/bin/bash
# Daily Backup Script for ty_learn Codespace
# Run this each morning to create systematic backups

set -e  # Exit on any error

# Configuration
BASE_DIR="/home/xai/Documents/ty_learn"
BACKUP_ROOT="$BASE_DIR/backup_system"
TODAY=$(date +%Y%m%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directories
DAILY_DIR="$BACKUP_ROOT/daily_backups/$TODAY"
mkdir -p "$DAILY_DIR"

echo "🚀 Starting Daily Backup - $TIMESTAMP"
echo "📁 Backup Location: $DAILY_DIR"

# Backup critical directories
echo "📂 Backing up ty_projects..."
cp -r "$BASE_DIR/ty_projects" "$DAILY_DIR/" 2>/dev/null || echo "⚠️ ty_projects not found"

echo "📂 Backing up scripts..."
cp -r "$BASE_DIR/scripts" "$DAILY_DIR/" 2>/dev/null || echo "⚠️ scripts not found"

echo "📂 Backing up modules..."
cp -r "$BASE_DIR/modules" "$DAILY_DIR/" 2>/dev/null || echo "⚠️ modules not found"

echo "📂 Backing up 0_mailboxes..."
cp -r "$BASE_DIR/0_mailboxes" "$DAILY_DIR/" 2>/dev/null || echo "⚠️ 0_mailboxes not found"

# Backup critical individual files
echo "📄 Backing up critical files..."
mkdir -p "$DAILY_DIR/root_files"
cp "$BASE_DIR"/*.md "$DAILY_DIR/root_files/" 2>/dev/null || echo "⚠️ No .md files in root"
cp "$BASE_DIR"/*.py "$DAILY_DIR/root_files/" 2>/dev/null || echo "⚠️ No .py files in root"
cp "$BASE_DIR"/*.ini "$DAILY_DIR/root_files/" 2>/dev/null || echo "⚠️ No .ini files in root"
cp "$BASE_DIR"/*.txt "$DAILY_DIR/root_files/" 2>/dev/null || echo "⚠️ No .txt files in root"
cp "$BASE_DIR"/*.toml "$DAILY_DIR/root_files/" 2>/dev/null || echo "⚠️ No .toml files in root"
cp "$BASE_DIR"/*.yaml "$DAILY_DIR/root_files/" 2>/dev/null || echo "⚠️ No .yaml files in root"

# Create backup manifest
echo "📋 Creating backup manifest..."
MANIFEST_FILE="$DAILY_DIR/BACKUP_MANIFEST_$TIMESTAMP.txt"
cat > "$MANIFEST_FILE" << EOF
Daily Backup Manifest
====================
Date: $TODAY
Timestamp: $TIMESTAMP
Backup Location: $DAILY_DIR

Directories Backed Up:
$(ls -la "$DAILY_DIR" | grep ^d | awk '{print "- " $9}' | grep -v "^\- \.$" | grep -v "^\- \.\.$")

File Counts:
$(find "$DAILY_DIR" -type f | wc -l) total files backed up

Critical Scripts Status:
$(ls -la "$BASE_DIR/backup_system/critical_scripts/" 2>/dev/null | grep "\.py$" | wc -l) critical scripts preserved

Disk Usage:
$(du -sh "$DAILY_DIR" | awk '{print $1}') total backup size
EOF

# Cleanup old daily backups (keep last 7 days)
echo "🧹 Cleaning up old backups..."
find "$BACKUP_ROOT/daily_backups" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null || true

# Summary
echo ""
echo "✅ Daily Backup Complete!"
echo "📊 Backup Summary:"
echo "   📁 Location: $DAILY_DIR"
echo "   📄 Manifest: $MANIFEST_FILE"
echo "   💾 Size: $(du -sh "$DAILY_DIR" | awk '{print $1}')"
echo "   📈 Files: $(find "$DAILY_DIR" -type f | wc -l) files backed up"
echo ""
echo "🛡️ Your codespace is now protected!"
