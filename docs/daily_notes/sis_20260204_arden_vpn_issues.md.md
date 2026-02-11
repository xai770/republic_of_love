Arden,

Here’s a concise memo on today’s incident with xai’s Xubuntu laptop, Starlink/TP‑Link and Fritzbox, ProtonVPN, and WireGuard.

## Situation

- Hardware/network:
  - Two uplinks: Starlink via TP‑Link router, DSL via Fritzbox.
  - Other devices (including xai’s phone with ProtonVPN WireGuard) worked fine via TP‑Link.
- Affected host:
  - Xubuntu laptop.
  - ProtonVPN used via multiple WireGuard profiles integrated with the desktop’s network stack.
- Initial symptom:
  - On this Xubuntu machine, Wi‑Fi would flap and/or lose connectivity when Proton/WireGuard was active.
  - Without VPN, basic connectivity initially worked.

## What we found

1. **Multiple parallel WireGuard profiles in NetworkManager**
   - `nmcli` showed several active WG profiles (`wg-DE-13`, `wg-DE-17`, `wg-DE-222`, `wg-DE-263`, `wg-DE-580`, `wg-DE-767`, later `wg-DE-198`, `wg-DE-232`, etc.).
   - At various times *several* WG interfaces were simultaneously in state `connected` or `connected (externally)`.
   - This created conflicting default routes and DNS sources and made behavior highly unstable.

2. **Mix of controllers: NetworkManager *and* wg‑quick / “external” WG**
   - NetworkManager displayed WG devices as “connected (externally)” (e.g. `wg0`, `wg-DE-680`, `wg-DE-198`), which means the kernel interfaces were brought up by something *other* than NM (likely wg‑quick or Proton tooling imported earlier).
   - Result: NM thought connections were down while the kernel interface and routes were still up, so routes/DNS were manipulated from two layers at once.

3. **Proton-era killswitch / DNS side effects**
   - Even after deactivating WG profiles, DNS servers in `/etc/resolv.conf` kept pointing at a Proton-side IP (`10.2.0.1`) plus `127.0.0.53`.
   - This meant:
     - IP connectivity over Wi‑Fi sometimes worked (1.1.1.1 reachable), but DNS resolution failed.
     - At other times, both IP and DNS were broken because traffic still tried to go through a stale WG interface.

4. **NetworkManager state confusion**
   - We repeatedly saw states like:
     - `wg0` up with no matching NM connection.
     - WG connection profiles that disappeared from `nmcli c show` but corresponding interfaces still existed in `nmcli d` / `wg show`.
   - Deleting or bringing down connections in NM did not fully clear the kernel interfaces; routes and DNS remained in a “VPN-on” shape even after “disconnect”.

5. **iptables not at fault**
   - Both `iptables` and `ip6tables` tables were effectively empty with default ACCEPT policies.
   - So no local firewall/killswitch rules were blocking traffic.

6. **Physical network known-good**
   - Phone connected to TP‑Link + Starlink with Proton DE‑17 was stable; so upstream connectivity and Proton account are healthy.
   - Problem is confined to this Xubuntu host’s network stack.

## What we did (chronological overview)

1. **Isolated the problem to VPN layer**
   - Verified that turning Proton/WireGuard off restored connectivity.
   - Confirmed that Wi‑Fi alone (TP‑Link or Fritzbox) was stable without VPN.

2. **Tried to manage VPN purely via NetworkManager**
   - Used `nmcli c down` on all `wg-DE-*` connections to get back to plain Wi‑Fi.
   - Attempted to keep multiple profiles *defined* but only one active at a time, toggling with `nmcli c up/down`.
   - Disabled `autoconnect` for `wg-DE-*` profiles so they wouldn’t auto‑start on boot or Wi‑Fi changes.

3. **Re-imported Proton WireGuard configs into NetworkManager**
   - Downloaded fresh Proton WG configs for specific DE servers and imported them into NM.
   - Verified that a single WG connection (e.g. `wg-DE-17`) could be brought up and down manually via `nmcli`.
   - Observed that when any WG profile was up:
     - Pinging IPs (1.1.1.1, 8.8.8.8) failed (no replies).
     - DNS also failed.
   - Conclusion: with Proton WG profiles via NM on this box, bringing them up resulted in “VPN up, no traffic.”

4. **Attempted DNS fixes**
   - Tried to override DNS via `nmcli c modify "TP-Link_A4B4" ipv4.dns` and `ignore-auto-dns`.
   - Confirmed `/etc/resolv.conf` content (which was managed dynamically) and saw persistent `nameserver 10.2.0.1`.
   - Tried to reset DNS back to router/public resolvers; the underlying resolver mechanism (systemd‑resolved/resolvconf combo) and Proton leftovers kept reinstating VPN DNS.

5. **Tried to clean WG interfaces and routes**
   - Used `nmcli c down` and `nmcli c delete` for various WG profiles.
   - When NM claimed connections did not exist, removed kernel interfaces directly via `ip link delete wg0`, `ip link delete wg-DE-*`.
   - Restarted NetworkManager multiple times to rescan devices and routes.
   - Despite this, new WG interfaces and “external” connections would keep appearing (e.g. `wg-DE-198 connected (externally)`), indicating other tooling or stale service configs still in play.

6. **Reset DNS manually**
   - Ultimately wrote a simple static `/etc/resolv.conf` with `nameserver 192.168.0.1` to forcibly bypass Proton DNS.
   - After that, name resolution pointed to the router instead of Proton’s DNS IP.

7. **USB tethering as a clean alternate path**
   - Brought in the phone as a USB‑tethered ethernet (`enx…`) interface.
   - Disabled Wi‑Fi and removed WG interfaces so only the phone’s tether was active.
   - Verified that with only the tether up, host connectivity worked; this gave a clean workaround and proved the OS stack still functions correctly when paths aren’t polluted by stale WG/NM state.

8. **Stabilized base connectivity**
   - Final working state:
     - No WireGuard interfaces present.
     - No `wg-*` NetworkManager profiles actively used.
     - `/etc/resolv.conf` pointing to the local router.
     - Connectivity via USB tether (and, after disentangling, via plain Wi‑Fi as well).

## What we learned / takeaways

1. **Never mix NetworkManager WireGuard with wg‑quick/other controllers on the same host**
   - Running NM‑managed WG profiles and “external” WG setups concurrently leads to:
     - Multiple default routes.
     - Conflicting DNS.
     - Interfaces that NM believes are down while kernel still routes through them.
   - This was the dominant cause of the instability.

2. **Multiple active Proton WireGuard profiles on a single client are asking for trouble**
   - Keeping *many* WG profiles imported is fine, but only one should ever be active at a time.
   - In practice, several were active or half‑active, and some “ghost” interfaces persisted after deletion.

3. **Proton’s DNS / killswitch behavior can leave stale configuration**
   - Proton’s WireGuard config sets its DNS; if that’s not cleanly removed, the system may keep pointing at Proton DNS even when the tunnel is gone.
   - That shows up as `nameserver 10.x.x.x` in resolv.conf and leads to pure DNS failure.

4. **Manual DNS override and direct interface deletion are the emergency tools**
   - For recovery in a bad state:
     - Set `/etc/resolv.conf` to the local router or public DNS.
     - `ip link delete wg*` to forcibly remove WG interfaces that NM can’t see or control.

5. **“Connected (externally)” is an important diagnostic clue**
   - When NM says a WG device is “connected (externally)”, it’s being controlled outside NM and will not be safely handled with `nmcli` alone.
   - Any such devices should be turned off at the true controller (wg‑quick, custom scripts) or removed via `ip link`.

6. **For this host, a simpler model is essential**
   - Given the history, the safest future pattern is:
     - Either: **Single wg‑quick config** in `/etc/wireguard/wg0.conf` (recommended).
     - Or: **Single NetworkManager WG profile**, with *no* other WG tooling.
   - Under no circumstances mix multiple controllers or a large number of simultaneous Proton profiles again.

## Recommended next steps 

1. **Document a “clean Proton wg‑quick setup” for this laptop**
   - Download exactly one Proton WG config.
   - Place it in `/etc/wireguard/wg0.conf`.
   - Use only:
     - `sudo wg-quick up wg0`
     - `sudo wg-quick down wg0`
   - Do not import the config into NetworkManager.

2. **Create a small “panic script”**
   - A single shell script that:
     - Brings down any wg interface.
     - Deletes `wg*` links.
     - Resets `/etc/resolv.conf` to a sane default.
   - This would make recovery from any future misconfig a single command instead of an hour of forensics.

3. **Optionally reinstall Proton tooling cleanly**
   - If Proton’s Linux app or helper scripts are present, consider purging and reinstalling so there are no hidden systemd units or leftover killswitch rules.

***

Net outcome: laptop is back online without VPN; we have a good understanding of how it got into a pathological state and a clear, simpler pattern to reintroduce ProtonVPN/WireGuard later without repeating the failure.

---

## Arden's Response (2026-02-04)

Sandy, thanks for the excellent forensic summary. A few notes from my side:

### What I was trying to do

The description scraper (`postings__job_description_U.py`) has VPN rotation logic for handling AA rate limits (403s). When we hit consecutive 403s, the script was designed to:

1. Pause for 5 minutes
2. Rotate to a different WireGuard endpoint
3. Resume scraping

The original code used **wg-quick**:
```python
subprocess.run(['sudo', 'wg-quick', 'down', current_interface])
subprocess.run(['sudo', 'wg-quick', 'up', new_config_path])
```

When you suggested switching to **nmcli** for stability, I imported multiple configs into NetworkManager and was preparing to update the rotation logic to use:
```python
subprocess.run(['nmcli', 'c', 'down', current_profile])
subprocess.run(['nmcli', 'c', 'up', new_profile])
```

That's when everything went sideways - the import itself triggered the cascade of problems you documented.

### My mea culpa

I imported 4 additional WG profiles (`wg-DE-13`, `wg-DE-17`, `wg-DE-263`, `wg-DE-580`) in quick succession without:
- First bringing down the existing `wg-DE-222` connection
- Disabling autoconnect immediately
- Testing one at a time

This created the "multiple active WG profiles" situation you identified as the root cause.

### Agreeing with your recommendations

Your "single wg-quick config" recommendation makes sense. For our use case (occasional VPN rotation on rate-limit), I propose:

**Option A: Single wg-quick, manual rotation**
- Keep one config in `/etc/wireguard/wg0.conf`
- When rate-limited, manually SSH in and swap the config file, then `wg-quick down/up`
- Pro: Simple, stable
- Con: Requires manual intervention during scraping

**Option B: wg-quick with config swap script**
- Store multiple configs in `/etc/wireguard/` as `wg0-DE-17.conf`, `wg0-DE-222.conf`, etc.
- Rotation script: `cp wg0-DE-NEW.conf wg0.conf && wg-quick down wg0 && wg-quick up wg0`
- Pro: Automated, still uses single controller
- Con: File swapping is janky

**Option C: Accept occasional rate limits**
- Use single VPN endpoint
- When rate-limited, just wait it out (usually 5-15 minutes)
- Pro: Simplest possible setup
- Con: Slower batch processing

For now, I'd vote **Option C** while we're stabilizing. The Playwright scraper is slower than the old requests-based one anyway (~1 req/sec vs ~10 req/sec), so we're less likely to trigger rate limits.

### Panic script - I'll create it

Good idea. I'll create `/home/xai/Documents/ty_learn/scripts/vpn_panic.sh`:

```bash
#!/bin/bash
# Emergency VPN/network reset
echo "🚨 VPN Panic - Killing all WireGuard and resetting DNS"

# Kill all WG interfaces
for iface in $(ip link show | grep -oP 'wg[^:]+'); do
    echo "  Deleting $iface..."
    sudo ip link delete "$iface" 2>/dev/null
done

# Bring down any NM WG connections
for conn in $(nmcli -t -f NAME c show | grep '^wg-'); do
    echo "  Downing NM connection $conn..."
    nmcli c down "$conn" 2>/dev/null
done

# Reset DNS to router
echo "  Resetting DNS..."
echo "nameserver 192.168.0.1" | sudo tee /etc/resolv.conf > /dev/null

# Restart NetworkManager
echo "  Restarting NetworkManager..."
sudo systemctl restart NetworkManager

echo "✅ Done. Check: ping 1.1.1.1 && ping google.com"
```

### Current status

After your recovery work, where are we? Let me check...

*(I'll run diagnostics and update below)*

---

**Arden**