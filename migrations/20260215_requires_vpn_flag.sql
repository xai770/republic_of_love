-- Migration: Flag local-only actors as not requiring VPN
-- Date: 2026-02-15
-- 
-- Actors that only use local resources (Ollama, database) don't need VPN rotation.
-- The turing_daemon reads execution_config.requires_vpn to skip VPN logic for these actors.

UPDATE actors SET execution_config = jsonb_set(COALESCE(execution_config, '{}'), '{requires_vpn}', 'false')
WHERE actor_name IN ('embedding_generator', 'extracted_summary', 'owl_pending_auto_triage');
