#!/bin/bash
# Pre-Change Backup Script
# Run this before making major modifications to protect your work

set -e

# Configuration
BASE_DIR="/home/xai/Documents/ty_learn"
BACKUP_ROOT="$BASE_DIR/backup_system"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Get parameters
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <target_directory> <description>"
    echo "Example: $0 ty_projects/v16_hybrid_framework V16_BUG_FIX"
    exit 1
fi

TARGET_DIR="$1"
DESCRIPTION="$2"

# Create backup directory
BACKUP_DIR="$BACKUP_ROOT/pre_change_backups/${TIMESTAMP}_${DESCRIPTION}"
mkdir -p "$BACKUP_DIR"

echo "🛡️ Pre-Change Backup Starting..."
echo "📁 Target: $TARGET_DIR"
echo "📝 Description: $DESCRIPTION"
echo "💾 Backup Location: $BACKUP_DIR"

# Validate target exists
if [ ! -e "$BASE_DIR/$TARGET_DIR" ]; then
    echo "❌ Error: Target directory/file '$TARGET_DIR' not found in $BASE_DIR"
    exit 1
fi

# Perform backup
echo "📂 Copying $TARGET_DIR..."
cp -r "$BASE_DIR/$TARGET_DIR" "$BACKUP_DIR/"

# Create backup info file
INFO_FILE="$BACKUP_DIR/BACKUP_INFO.txt"
cat > "$INFO_FILE" << EOF
Pre-Change Backup Information
============================
Timestamp: $TIMESTAMP
Description: $DESCRIPTION
Target: $TARGET_DIR
Backup Location: $BACKUP_DIR

Original Location: $BASE_DIR/$TARGET_DIR
Backup Size: $(du -sh "$BACKUP_DIR" | awk '{print $1}')
File Count: $(find "$BACKUP_DIR" -type f | wc -l) files

Backup Created By: Arden's Backup System
Purpose: Protect against modification/corruption during changes

Recovery Command:
cp -r "$BACKUP_DIR/$(basename "$TARGET_DIR")" "$BASE_DIR/$(dirname "$TARGET_DIR")/"
EOF

echo "✅ Pre-Change Backup Complete!"
echo "📊 Summary:"
echo "   💾 Size: $(du -sh "$BACKUP_DIR" | awk '{print $1}')"
echo "   📄 Files: $(find "$BACKUP_DIR" -type f | wc -l) files"
echo "   📋 Info: $INFO_FILE"
echo ""
echo "🎯 You can now safely make changes to $TARGET_DIR"
echo "🔄 Recovery: cp -r \"$BACKUP_DIR/$(basename "$TARGET_DIR")\" \"$BASE_DIR/$(dirname "$TARGET_DIR")/\""
