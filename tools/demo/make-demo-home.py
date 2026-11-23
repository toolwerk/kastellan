#!/usr/bin/env python3
"""Erzeugt ein Datenverzeichnis mit erfundenen Verbindungen, Rechten, Freigaben und Protokoll.

Zweck: Screenshots für die README, ohne echte Konten und Domains zu zeigen.

    tools/demo/make-demo-home.py /pfad/zum/demo-home
    KASTELLAN_HOME=/pfad/zum/demo-home /Applications/Kastellan.app/Contents/MacOS/Kastellan

Alle Namen, Domains und Adressen sind erfunden (Domains unter .example, Adressen aus 203.0.113.0/24).
Zugangsdaten legt das Skript nicht an. Die App meldet deshalb beim Prüfen "Zugangsdaten fehlen",
der Gesundheitsstand kommt aus health.jsonl.
"""
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

if len(sys.argv) != 2:
    sys.exit(__doc__)
home = sys.argv[1]
for d in ("", "policies", "pending"):
    os.makedirs(os.path.join(home, d), exist_ok=True)
    os.chmod(os.path.join(home, d), 0o700)

now = datetime.now(timezone.utc).replace(microsecond=0)


def ts(minutes_ago):
    return (now - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, "kastellan-demo-" + name))


def write(name, data, lines=False):
    path = os.path.join(home, name)
    with open(path, "w") as f:
        if lines:
            f.write("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in data))
        else:
            json.dump(data, f, indent=2, ensure_ascii=False)
    os.chmod(path, 0o600)


profile = uid("profil")
write("profiles.json", [{"id": profile, "name": "Beispiel Agentur", "created_at": ts(60 * 24 * 30)}])

conns = [
    ("kas", "allinkl", "Webhosting Hauptkonto", {"kas_login": "w0123456"}, "KAS-Login w0123456 erreichbar"),
    ("cf", "cloudflare", "Cloudflare Agentur", {"account_id": "0123456789abcdef0123456789abcdef"}, "Token gültig, 4 Zonen"),
    ("hz", "hetzner", "Hetzner Projekt Web", {"project": "web-prod"}, "Projekt web-prod erreichbar, 3 Server"),
    ("hde", "hostingde", "hosting.de Kunden", {}, "API-Key gültig, 11 Domains"),
    ("mw", "mittwald", "Mittwald Shop", {}, "Token gültig, 2 Projekte"),
    ("hg", "hostinger", "Hostinger Blog", {}, "Token gültig, 5 Domains"),
    ("nc", "namecheap", "Namecheap Marken", {"api_user": "beispiel", "client_ip": "203.0.113.10"}, "API erreichbar, 6 Domains"),
]
write("connections.json", [
    {"id": uid(k), "provider": p, "label": label, "profile_id": profile, "settings": s, "created_at": ts(60 * 24 * 20)}
    for k, p, label, s, _ in conns
])
write("health.jsonl", [
    {"connection_id": uid(k), "checked_at": ts(4 + i), "ok": True, "message": msg}
    for i, (k, _, _, _, msg) in enumerate(conns)
], lines=True)

assignments = [
    ("kas", "beispiel.example", ["dns_zone", "dns_record", "mailbox", "mail_forward", "cron_job"]),
    ("kas", "muster-agentur.example", ["dns_zone", "dns_record", "mailbox", "mail_forward"]),
    ("cf", "kundenprojekt.example", ["dns_zone", "dns_record"]),
    ("hde", "stadtwerk-beispiel.example", ["dns_zone", "dns_record", "domain", "mailbox"]),
    ("mw", "shop-beispiel.example", ["dns_zone", "dns_record", "database", "cron_job"]),
    ("hg", "blog-beispiel.example", ["dns_zone", "dns_record", "domain"]),
    ("nc", "marke-beispiel.example", ["domain", "dns_record", "mail_forward"]),
]
write("assignments.json", [
    {"id": uid("zu-" + d), "profile_id": profile, "connection_id": uid(k), "domain": d, "resources": r}
    for k, d, r in assignments
])

clients = [("Claude Code", "code"), ("Claude Desktop", "desktop")]
write("tokens.json", [
    {"id": uid("token-" + slug), "client": c, "profile_id": profile, "created_at": ts(60 * 24 * 10),
     "token_hash": hashlib.sha256(slug.encode()).hexdigest(), "last_used_at": ts(12)}
    for c, slug in clients
])


def policy(level_by_conn):
    out = {}
    for k, levels in level_by_conn.items():
        out[uid(k)] = {
            "permissions": levels, "domains": [], "exclude": [], "confirm_extra": [],
            "scopes": {"record_types": []}, "agent_may_confirm": False, "reveal_generated_passwords": False,
        }
    return out


write("policies/beispiel-agentur-claude-code.json", {"profile": "beispiel-agentur", "client": "Claude Code", "connections": policy({
    "kas": {"domain": "read", "dns_zone": "write", "dns_record": "write", "mailbox": "write", "mail_forward": "write", "cron_job": "read"},
    "cf": {"dns_zone": "write", "dns_record": "write", "certificate": "read"},
    "hz": {"server": "read", "firewall": "read", "ssh_user": "read", "dns_record": "write"},
    "hde": {"domain": "read", "dns_record": "write", "mailbox": "read"},
    "mw": {"database": "read", "cron_job": "read", "dns_record": "write"},
    "hg": {"domain": "read", "dns_record": "read"},
    "nc": {"domain": "read", "dns_record": "write", "mail_forward": "write"},
})})
write("policies/beispiel-agentur-claude-desktop.json", {"profile": "beispiel-agentur", "client": "Claude Desktop", "connections": policy({
    "kas": {"domain": "read", "dns_record": "read", "mailbox": "read", "mail_forward": "read"},
    "cf": {"dns_zone": "read", "dns_record": "read"},
    "hz": {"server": "read"},
})})


def pending(key, status, minutes_ago, resource, action, target, preview, params, result=None):
    p = {
        "id": uid("pending-" + key), "client": "Claude Code", "connection_id": uid(key.split(":")[0]),
        "capability": {"resource": resource, "action": action}, "target": target, "parameters": params,
        "preview": preview, "status": status, "created_at": ts(minutes_ago),
    }
    if status in ("confirmed", "done"):
        p["decided_at"] = ts(minutes_ago - 1)
    if status == "done":
        p["finished_at"] = ts(minutes_ago - 1)
        p["result"] = result or {"deleted": target}
    write("pending/%s.json" % p["id"], p)


pending("kas:1", "prepared", 7, "mailbox", "delete", "alt@beispiel.example",
        "Postfach alt@beispiel.example löschen. Alle Mails darin gehen verloren.", {"address": "alt@beispiel.example"})
pending("nc:1", "prepared", 3, "domain", "update", "marke-beispiel.example",
        "Nameserver von marke-beispiel.example ändern auf ns1.dns-beispiel.example und ns2.dns-beispiel.example.",
        {"nameservers": ["ns1.dns-beispiel.example", "ns2.dns-beispiel.example"]})
pending("cf:1", "prepared", 1, "dns_record", "delete", "MX kundenprojekt.example",
        "MX-Record von kundenprojekt.example löschen (Priorität 10, mail.kundenprojekt.example).", {"type": "MX"})
pending("kas:2", "done", 95, "mail_forward", "delete", "info@muster-agentur.example",
        "Weiterleitung info@muster-agentur.example löschen.", {"address": "info@muster-agentur.example"},
        {"deleted": "info@muster-agentur.example"})

audit = []
n = [0]


def log(minutes_ago, tool, key, outcome="ok", target=None, message=None, client="Claude Code", cap=None, dur=0):
    n[0] += 1
    e = {"id": uid("audit-%d" % n[0]), "timestamp": ts(minutes_ago), "client": client,
         "connection_id": uid(key), "outcome": outcome, "duration_ms": dur}
    if tool:
        e["tool"] = tool
    if target:
        e["target"] = target
    if message:
        e["message"] = message
    if cap:
        e["capability"] = {"resource": cap[0], "action": cap[1]}
    audit.append(e)


log(240, "kastellan_list_connections", "kas", dur=2)
log(236, "domain_list", "kas", cap=("domain", "list"), dur=410)
log(235, "dns_record_list", "kas", target="beispiel.example", cap=("dns_record", "list"), dur=520)
log(220, "mailbox_list", "kas", target="beispiel.example", cap=("mailbox", "list"), dur=380)
log(180, "dns_record_create", "cf", target="TXT kundenprojekt.example", cap=("dns_record", "create"), dur=640)
log(150, "server_list", "hz", cap=("server", "list"), dur=300, client="Claude Desktop")
log(140, "dns_record_list", "hde", target="stadtwerk-beispiel.example", cap=("dns_record", "list"), dur=450)
log(120, "database_list", "mw", cap=("database", "list"), dur=360)
log(110, "dns_record_list", "nc", target="marke-beispiel.example", cap=("dns_record", "list"), dur=700)
log(96, None, "kas", outcome="pending", target="info@muster-agentur.example", cap=("mail_forward", "delete"))
log(95, None, "kas", outcome="confirmed", target="info@muster-agentur.example", cap=("mail_forward", "delete"), client="Kastellan")
log(60, "dns_record_update", "hg", outcome="denied", target="blog-beispiel.example", cap=("dns_record", "update"),
    message="Recht dns_record:write fehlt (Stufe read)")
log(40, "dns_record_list", "cf", outcome="out_of_scope", target="fremde-domain.example", cap=("dns_record", "list"),
    message="fremde-domain.example liegt nicht im Bereich dieser Verbindung")
log(20, "kastellan_list_connections", "kas", dur=2)
log(14, "domain_get", "kas", target="beispiel.example", cap=("domain", "get"), dur=330)
log(8, None, "kas", outcome="pending", target="alt@beispiel.example", cap=("mailbox", "delete"))
log(4, None, "nc", outcome="pending", target="marke-beispiel.example", cap=("domain", "update"))
log(2, None, "cf", outcome="pending", target="MX kundenprojekt.example", cap=("dns_record", "delete"))
write("audit.jsonl", audit, lines=True)

with open(os.path.join(home, "settings.json"), "w") as f:
    json.dump({"keep_in_dock": True, "show_in_menu_bar": False, "text_size_step": 3}, f, indent=2)
print("Beispiel-Daten liegen in", home)
