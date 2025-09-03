#!/bin/bash
# V16.2 Framework Recovery Script
# Quick recovery for V16.2 focused testing components

BACKUP_BASE="/home/xai/Documents/ty_learn/backup_system"
TARGET_DIR="/home/xai/Documents/ty_learn/ty_projects/v16_hybrid_framework/v16.2_testing"

echo "🚑 V16.2 Framework Recovery Options"
echo "=================================="
echo ""

# Find latest backups
echo "📋 Available V16.2 Backups:"
echo ""

echo "🔧 Critical Scripts:"
ls -1t "$BACKUP_BASE/critical_scripts/" | grep "v16_focused_testing" | head -3 | nl

echo ""
echo "📁 Complete Directory Backups:"
ls -1t "$BACKUP_BASE/v16_framework_backups/" | grep "v16.2_testing" | head -3 | nl

echo ""
echo "📦 Pre-Change Backups:"
ls -1t "$BACKUP_BASE/pre_change_backups/" | grep "V16.2" | head -3 | nl

echo ""
echo "🎯 Quick Recovery Commands:"
echo ""

# Get latest critical script backup
LATEST_SCRIPT=$(ls -1t "$BACKUP_BASE/critical_scripts/" | grep "v16_focused_testing" | head -1)
if [ -n "$LATEST_SCRIPT" ]; then
    echo "📜 Restore Latest Script:"
    echo "   cp \"$BACKUP_BASE/critical_scripts/$LATEST_SCRIPT\" \"$TARGET_DIR/v16_focused_testing.py\""
    echo ""
fi

# Get latest complete backup
LATEST_COMPLETE=$(ls -1t "$BACKUP_BASE/v16_framework_backups/" | grep "v16.2_testing" | head -1)
if [ -n "$LATEST_COMPLETE" ]; then
    echo "📁 Restore Complete Directory:"
    echo "   rm -rf \"$TARGET_DIR\""
    echo "   cp -r \"$BACKUP_BASE/v16_framework_backups/$LATEST_COMPLETE\" \"$TARGET_DIR\""
    echo ""
fi

# Get latest pre-change backup
LATEST_PRECHANGE=$(ls -1t "$BACKUP_BASE/pre_change_backups/" | grep "V16.2" | head -1)
if [ -n "$LATEST_PRECHANGE" ]; then
    echo "🔄 Restore Pre-Change Backup:"
    echo "   cp \"$BACKUP_BASE/pre_change_backups/$LATEST_PRECHANGE/v16_focused_testing.py\" \"$TARGET_DIR/\""
    echo ""
fi

echo "⚠️  Always verify file integrity after recovery!"
echo "✅ Test with: python3 -c \"from v16_focused_testing import V16FocusedTester; print('✅ Import successful')\""
