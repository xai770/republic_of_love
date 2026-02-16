"""
Signal notification helper — send pipeline alerts via signal-cli.

Usage:
    from lib.signal_notify import send_alert, send_pipeline_summary

    # Simple alert
    send_alert("Pipeline step 3 failed: 47 errors in berufenet classification")

    # Pipeline summary (end of run)
    send_pipeline_summary(steps=[
        {"name": "AA fetch", "ok": True, "count": 1200},
        {"name": "Berufenet", "ok": True, "count": 800, "errors": 3},
        {"name": "Embeddings", "ok": False, "count": 0, "errors": 47},
    ], duration_sec=845)

Setup (one-time):
    # Option A: Link as secondary device to your Signal account
    signal-cli link -n "arden-server" | head -1
    # → Shows a tslink:// URI — open it as QR code in Signal app → Settings → Linked Devices

    # Option B: Register a new number (needs SMS verification)
    signal-cli -a +49XXXXXXXXXX register
    signal-cli -a +49XXXXXXXXXX verify CODE

Configuration:
    Set SIGNAL_SENDER and SIGNAL_RECIPIENT in .env or environment:
        SIGNAL_SENDER=+49...        # The registered/linked account
        SIGNAL_RECIPIENT=+4915125098515
"""
import subprocess
import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Load .env from project root
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

# Config — loaded from env or .env
SIGNAL_CLI = os.getenv("SIGNAL_CLI", os.path.expanduser("~/.local/bin/signal-cli"))
SIGNAL_SENDER = os.getenv("SIGNAL_SENDER", "")
SIGNAL_RECIPIENT = os.getenv("SIGNAL_RECIPIENT", "+4915125098515")

# Prefix for all messages
PREFIX = "🏗️ talent.yoga"


def _signal_available() -> bool:
    """Check if signal-cli is installed and a sender is configured."""
    if not SIGNAL_SENDER:
        logger.debug("SIGNAL_SENDER not set — Signal notifications disabled")
        return False
    if not os.path.isfile(SIGNAL_CLI):
        logger.warning("signal-cli not found at %s", SIGNAL_CLI)
        return False
    return True


def send_signal(message: str, recipient: Optional[str] = None) -> bool:
    """
    Send a Signal message. Returns True on success, False on failure.
    Never raises — alerting should not crash the pipeline.
    """
    if not _signal_available():
        logger.info("Signal not available, would have sent: %s", message[:100])
        return False

    target = recipient or SIGNAL_RECIPIENT
    try:
        result = subprocess.run(
            [SIGNAL_CLI, "-a", SIGNAL_SENDER, "send", "-m", message, target],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            logger.info("Signal alert sent to %s", target)
            return True
        else:
            logger.error("signal-cli failed (rc=%d): %s", result.returncode, result.stderr[:200])
            return False
    except subprocess.TimeoutExpired:
        logger.error("signal-cli timed out (30s)")
        return False
    except Exception as e:
        logger.error("Signal send failed: %s", e)
        return False


def send_alert(message: str, recipient: Optional[str] = None) -> bool:
    """Send a prefixed alert message."""
    return send_signal(f"{PREFIX} ⚠️\n{message}", recipient)


def send_pipeline_summary(steps: list[dict], duration_sec: float,
                          recipient: Optional[str] = None) -> bool:
    """
    Send a pipeline run summary.

    Each step dict: {"name": str, "ok": bool, "count": int, "errors": int}
    """
    lines = [f"{PREFIX} — Pipeline Complete"]
    lines.append(f"Duration: {duration_sec/60:.1f} min")
    lines.append("")

    total_errors = 0
    for s in steps:
        ok = s.get("ok", True)
        errors = s.get("errors", 0)
        total_errors += errors
        icon = "✅" if ok else "❌"
        line = f"{icon} {s['name']}"
        if "count" in s:
            line += f" ({s['count']:,} items)"
        if errors:
            line += f" — {errors} errors"
        lines.append(line)

    lines.append("")
    if total_errors == 0:
        lines.append("All clear. 🟢")
    else:
        lines.append(f"Total errors: {total_errors} 🔴")

    return send_signal("\n".join(lines), recipient)


def send_error(step_name: str, error_count: int, sample_error: str = "",
               recipient: Optional[str] = None) -> bool:
    """Send an immediate error alert for a pipeline step."""
    msg = f"{PREFIX} ❌ {step_name}\n{error_count} errors"
    if sample_error:
        msg += f"\n\nSample: {sample_error[:300]}"
    return send_signal(msg, recipient)


# ---------------------------------------------------------------------------
# CLI interface — test from command line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
    else:
        msg = "Test alert from Arden 🔔"

    if not SIGNAL_SENDER:
        print("SIGNAL_SENDER not set. To test:")
        print("  SIGNAL_SENDER=+49... python -m lib.signal_notify 'hello'")
        print("\nSetup instructions:")
        print("  1. Link as secondary device:")
        print("     signal-cli link -n 'arden-server'")
        print("     (scan QR in Signal app → Settings → Linked Devices)")
        print("  2. Set env vars:")
        print("     echo 'SIGNAL_SENDER=+4915125098515' >> .env")
        print("     echo 'SIGNAL_RECIPIENT=+4915125098515' >> .env")
        sys.exit(1)

    ok = send_alert(msg)
    print("Sent!" if ok else "Failed — check logs")
