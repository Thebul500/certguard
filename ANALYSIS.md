# CertGuard — Competitive Analysis

> Research conducted March 2026. The SSL/TLS certificate monitoring space is active and
> increasingly relevant due to the CA/B Forum's April 2025 decision to reduce certificate
> lifespans to 47 days by 2029 (phased rollout starting March 2026 with 200-day certs).

---

## Existing Tools

### 1. CertMate — `fabriziosalmi/certmate`

- **GitHub:** ~1.2k stars, 79 forks
- **Language:** Python
- **Status:** Actively maintained (commits in 2026)
- **What it does:** Full certificate lifecycle management — automated renewal via ACME/DNS-01,
  RBAC, multi-CA support (Let's Encrypt, DigiCert, private CAs), real-time dashboard with SSE,
  REST API with Swagger docs.
- **Key features:** 22 DNS providers, multi-account support, storage backends (local, Azure Key
  Vault, AWS Secrets Manager, HashiCorp Vault), Docker/K8s deployment, notification via Email,
  Slack, Discord, generic webhooks.
- **User complaints:** Open issues around third-party storage support (#18), complexity of
  initial setup. The tool is heavily oriented toward certificate *issuance and renewal* rather
  than *inventory and discovery*. You need to already know what certs you have.
- **Gap for us:** CertMate doesn't scan your network to discover certificates. It manages certs
  it issues. If you have certs from multiple sources (purchased, self-signed, Let's Encrypt,
  internal CA), CertMate won't give you a unified inventory.

### 2. ssl_exporter — `ribbybibby/ssl_exporter`

- **GitHub:** ~590 stars, 107 forks
- **Language:** Go
- **Status:** Last commit Nov 2024, mature project
- **What it does:** Prometheus exporter that probes TLS endpoints and exposes certificate
  metadata as metrics (`ssl_cert_not_after`, `ssl_cert_not_before`, etc.).
- **Key features:** TCP probes, HTTPS probes, local PEM file scanning, Kubernetes secret
  scanning, kubeconfig parsing. Flexible labeling for Grafana dashboards and Alertmanager rules.
- **User complaints:** Requires full Prometheus + Grafana stack — significant operational
  overhead for small teams. Self-signed cert handling is awkward (need to provide CA certs
  explicitly). Chain of trust only represents exporter-to-target path, not real client paths.
  Timeout handling tied to Prometheus scrape config.
- **Gap for us:** This is a *metrics exporter*, not a standalone tool. You need Prometheus,
  Grafana, and Alertmanager already running. No built-in alerting, no dashboard, no inventory
  database. For homelabs and small teams without a monitoring stack, this is a non-starter.

### 3. ssl-cert-check — `Matty9191/ssl-cert-check`

- **GitHub:** ~781 stars, 292 forks
- **Language:** Shell (100%)
- **Status:** Mature but aging, sporadic maintenance
- **What it does:** Bourne shell script that checks certificate expiry dates and sends email
  alerts or Nagios notifications. Designed to run from cron.
- **Key features:** Check remote hosts, local PEM/PKCS12 files, directory scanning. Batch mode
  via config file. Configurable expiry thresholds. Email and Nagios output.
- **User complaints:** Multiple open issues around OpenSSL compatibility breakage (#55, #69).
  Timeout utility not available on all platforms (#17, #45). Temp file errors (#60, #105) where
  openssl fails silently. DOS/Unix line ending issues in config files. Email `from` address
  handling broken in latest version (#110). No API, no dashboard, no structured output — it's
  a shell script from the 2010s.
- **Gap for us:** Shell scripts don't scale. No REST API, no database, no dashboard, no
  webhook/Signal notifications. You can't query historical cert data. You can't build
  automation on top of it. It's a cron job that sends email, nothing more.

### 4. cert-checker — `mogensen/cert-checker`

- **GitHub:** ~132 stars, 27 forks
- **Language:** Go
- **Status:** Last release June 2021, effectively unmaintained
- **What it does:** Monitors TLS certificates and exposes results as Prometheus metrics. Includes
  a built-in web dashboard. Checks for expired certs, hostname mismatches, weak ciphers, and
  TLS version support.
- **Key features:** Built-in dashboard (unlike ssl_exporter), Grafana integration, Kubernetes
  deployment via Helm/Kustomize, no root required, checks cipher suites and TLS versions.
- **User complaints:** Unmaintained since 2021 — no updates for 5 years. YAML-only config with
  no autodiscovery. Still requires Prometheus for alerting. Dependencies are outdated.
- **Gap for us:** Abandoned project. The built-in dashboard concept is good but the execution is
  dead. No API, no persistence, no notification system. Config is static YAML — you must
  manually list every host to monitor.

### 5. Cert Spotter — `SSLMate/certspotter`

- **GitHub:** ~1.1k stars, 99 forks
- **Language:** Go
- **Status:** Actively maintained (Dec 2024)
- **What it does:** Certificate Transparency (CT) log monitor. Watches CT logs for certificates
  issued for your domains. Detects unauthorized issuance, DNS compromise, subdomain takeover.
- **Key features:** No database required, robust cert parser (handles null-prefix attacks),
  watches entire domain trees, email and hook-script notifications, log auditing.
- **User complaints:** Only monitors CT logs — it tells you when someone *issues* a cert for
  your domain, but doesn't check if your *deployed* certs are expired or misconfigured. Not a
  scanner or inventory tool. Different problem space.
- **Gap for us:** Complementary, not competing. Cert Spotter watches for new issuance; CertGuard
  would watch what's actually deployed and expiring on your infrastructure.

### 6. certificate-expiry-monitor — `muxinc/certificate-expiry-monitor`

- **GitHub:** ~166 stars, 24 forks
- **Language:** Go
- **Status:** Maintained
- **What it does:** Kubernetes-focused tool that discovers pods via the K8s API, checks their TLS
  certificates, and exposes Prometheus metrics for expiry, issuance, and status.
- **Key features:** Kubernetes-native autodiscovery via label selectors, per-pod/per-domain
  metrics, designed for K8s clusters.
- **User complaints:** Kubernetes-only. Completely useless if you're running bare-metal servers,
  VMs, Docker Compose, or any non-K8s infrastructure. Requires Prometheus.
- **Gap for us:** Assumes Kubernetes. Most homelabs, small businesses, and mixed infrastructure
  environments don't run K8s. CertGuard targets the Docker Compose / bare-metal / VM crowd.

### 7. CZERTAINLY

- **GitHub:** ~50 stars across repos
- **Language:** Java
- **Status:** Actively maintained, enterprise-focused
- **What it does:** Full certificate lifecycle management platform — inventory, issuance,
  revocation, renewal, cryptographic key management.
- **Key features:** Technology-agnostic, connector-based architecture, REST API, RBAC, audit
  logging, compliance reporting.
- **User complaints:** Massively overengineered for small deployments. Java-based microservice
  architecture requires significant resources. Documentation is enterprise-heavy. Deployment
  is complex (multiple containers, database, message queue).
- **Gap for us:** Enterprise PKI platform, not a lightweight monitoring tool. Deploying
  CZERTAINLY to watch 20 certificates is like using an aircraft carrier to cross a lake.

---

## Gap Analysis

After reviewing the landscape, there is a clear gap in the market:

**No lightweight, self-contained, API-first certificate inventory and monitoring tool exists
for small-to-medium infrastructure outside of Kubernetes.**

The current options fall into these buckets:

| Category | Tools | Problem |
|---|---|---|
| Shell scripts / cron jobs | ssl-cert-check | No API, no dashboard, no persistence, fragile |
| Prometheus exporters | ssl_exporter, cert-checker, mux/cert-expiry-monitor | Require full monitoring stack (Prometheus + Grafana + Alertmanager) |
| Kubernetes-native | cert-manager, mux/cert-expiry-monitor | Useless outside K8s |
| Enterprise platforms | CZERTAINLY, CertMate | Overkill for <100 certs, complex deployment |
| CT monitors | Cert Spotter | Different problem (issuance, not deployment) |

**Specific unmet needs identified:**

1. **Network scanning + inventory in one tool.** No existing tool scans arbitrary hosts/subnets
   to *discover* certificates AND stores them in a queryable database. You either get a scanner
   (certificate-inventory, ssl-cert-check) that dumps CSV/text, or a manager (CertMate) that
   only tracks certs it issued.

2. **Signal / webhook alerting without Prometheus.** Every alerting solution requires either
   email (outdated for homelabs) or a full Prometheus stack. Nobody supports Signal, ntfy,
   Gotify, or other self-hosted notification channels out of the box. CertMate has webhooks but
   no Signal integration.

3. **REST API + dashboard without enterprise complexity.** CZERTAINLY has the API but requires a
   Java microservice fleet. CertMate has the dashboard but focuses on issuance, not inventory.
   cert-checker had a dashboard but is dead. There's no simple Docker Compose-deployable tool
   with both.

4. **Historical tracking.** None of the lightweight tools track certificate changes over time.
   When did this cert rotate? What was the previous issuer? Did the SANs change? This data is
   lost with scan-and-forget tools.

5. **47-day cert readiness.** With certificate lifespans dropping to 200 days in March 2026
   and 47 days by 2029, the *frequency* of cert rotation is about to increase 8x. Tools that
   run as daily cron jobs won't cut it. Infrastructure needs continuous monitoring with
   configurable alert thresholds that account for rapid rotation cycles.

---

## Differentiator

CertGuard fills the gap as a **lightweight, self-hosted certificate inventory and monitoring
tool designed for non-Kubernetes infrastructure** (Docker Compose, bare metal, VMs, homelabs,
small teams).

**What makes CertGuard different:**

1. **Scan-first architecture.** Point it at hosts, subnets, or port ranges. It discovers
   certificates automatically and builds an inventory. You don't need to already know what
   certs you have.

2. **Persistent inventory with history.** PostgreSQL-backed storage tracks every certificate
   scan. See when certs rotated, what changed, and trend toward expiry. Query via REST API.

3. **Signal-native alerting.** First-class integration with Signal REST API for expiry alerts —
   built for the self-hosted/homelab crowd that uses Signal, not PagerDuty. Also supports
   generic webhooks for ntfy, Gotify, Slack, etc.

4. **Zero monitoring stack required.** No Prometheus, no Grafana, no Alertmanager. One container
   (+ PostgreSQL) gives you a REST API, scheduled scanning, and alerting. `docker compose up`
   and you're running.

5. **47-day cert lifecycle ready.** Configurable scan intervals and alert thresholds designed
   for the upcoming era of short-lived certificates. Background scheduler re-scans on intervals
   measured in hours, not days.

6. **API-first design.** Every feature accessible via REST API with Pydantic-validated schemas.
   Build automation, integrate with CI/CD, trigger renewal hooks programmatically.

**Honest assessment:** CertMate is the closest competitor and is a strong project. If your
primary need is *issuing and renewing* Let's Encrypt certificates with a dashboard, use CertMate.
CertGuard targets a different use case: *discovering, inventorying, and monitoring* certificates
across mixed infrastructure regardless of how they were issued. The two tools are complementary
— CertMate manages cert lifecycle, CertGuard monitors what's actually deployed.
