# External References

This document lists all external symlinks and their real paths for portability reference.

## Symlinked Directories

| Link in Repo | Real Path | Purpose | Owner |
|---------------|-----------|---------|-------|
| `0_mailboxes` | `/home/xai/Documents/0_mailboxes` | Mailbox system | External |
| `ty_projects` | `/home/xai/Documents/ty_projects` | Project data | External |
| `rfa_latest` | `/home/xai/Documents/ty_rfa/rfa_latest` | RfA documents | External |
| `ty_log` | `../ty_log` | Logging system | External |

## Portability Notes

When moving this workspace to another environment:

1. **Create target directories** or update symlinks to new paths
2. **Check dependencies** - some scripts may reference these paths
3. **Update paths** in configuration files if needed
4. **Test functionality** after relinking to ensure all integrations work

## Local Development

For local development, ensure these external systems are available:
- RfA system for documentation workflow
- Mailbox system for communication tracking  
- Project data for processing pipelines
- Logging system for operational monitoring

