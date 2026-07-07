# SMTP setup on Ubuntu 24.04 (for suomisf password-reset email)

Goal: let the suomisf backend send transactional email (password-reset
links) reliably. The app talks to a **local Postfix** on `localhost:25`,
and Postfix relays outbound mail through a **smarthost** (a transactional
email provider). This keeps mail code trivial and gives good
deliverability without running a full public mail server.

> TL;DR of the decision: **do not deliver mail directly from the app
> server.** Home/VPS IPs are usually blocked or land in spam. Relay
> through a provider that gives you SPF/DKIM and a clean sending IP.

---

## 0. Prerequisites

- A sending domain you control (e.g. `sofistes.net`) so you can add DNS
  records.
- An account with a transactional email provider that exposes SMTP
  (host, port `587`, username, password / API key). Examples of the
  shape you need: `smtp.<provider>.com:587` + user + pass.
- `sudo` on the Ubuntu 24.04 host that runs the backend.

Outbound port **25 is commonly blocked** by ISPs/clouds; that is why we
relay on **port 587 (submission)** to the smarthost, not port 25.

---

## 1. Install Postfix

```bash
sudo apt update
sudo apt install -y postfix mailutils
```

In the debconf prompt choose **"Internet Site"** (or "Satellite system"
if offered and you only relay). System mail name: your domain, e.g.
`sofistes.net`. You can reconfigure later:

```bash
sudo dpkg-reconfigure postfix
```

---

## 2. Configure Postfix as a send-only relay

Edit `/etc/postfix/main.cf`. Set / confirm these keys:

```ini
# Identity
myhostname = mail.sofistes.net
myorigin = /etc/mailname          # contains your domain

# Listen only on localhost — NOT a public mail server / open relay
inet_interfaces = loopback-only
inet_protocols = ipv4

# Only accept mail from the local machine
mynetworks = 127.0.0.0/8 [::1]/128

# Relay everything outbound through the smarthost on submission port 587
relayhost = [smtp.YOUR-PROVIDER.com]:587

# SASL auth to the smarthost
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
smtp_sasl_security_options = noanonymous
smtp_sasl_mechanism_filter = plain, login

# TLS to the smarthost
smtp_tls_security_level = encrypt
smtp_tls_CAfile = /etc/ssl/certs/ca-certificates.crt

# Do not accept inbound mail for any domain
mydestination =
relay_domains =
```

The square brackets around the relayhost (`[smtp...]`) skip an MX lookup
and connect directly to that host.

---

## 3. Store the smarthost credentials

```bash
sudo tee /etc/postfix/sasl_passwd >/dev/null <<'EOF'
[smtp.YOUR-PROVIDER.com]:587 USERNAME:PASSWORD
EOF

sudo chmod 600 /etc/postfix/sasl_passwd
sudo postmap /etc/postfix/sasl_passwd      # builds sasl_passwd.db
sudo chmod 600 /etc/postfix/sasl_passwd.db
```

Reload:

```bash
sudo systemctl restart postfix
sudo systemctl enable postfix
```

Whenever you edit `sasl_passwd`, re-run `postmap` and restart Postfix.

---

## 4. Test delivery

Install `swaks` for a clean end-to-end test:

```bash
sudo apt install -y swaks
swaks --to you@example.com --from noreply@sofistes.net \
      --server 127.0.0.1:25
```

Or the quick built-in way:

```bash
echo "test body" | mail -s "suomisf smtp test" \
    -a "From: noreply@sofistes.net" you@example.com
```

Watch the mail log while testing:

```bash
sudo tail -f /var/log/mail.log
```

A successful relay shows `status=sent` and the provider's queue id. If
you see `status=bounced`/`deferred`, the message there names the cause
(auth failure, TLS, blocked port, DNS, etc.).

---

## 5. DNS records (required for inbox delivery)

Set these on the **sending domain**. Exact values come from your
provider's dashboard; the record *types* are always:

- **SPF** (TXT on the domain) — authorises the provider to send for you,
  e.g. `v=spf1 include:_spf.YOUR-PROVIDER.com -all`.
- **DKIM** (CNAME/TXT the provider gives you) — cryptographic signing.
- **DMARC** (TXT at `_dmarc.sofistes.net`) — start monitoring:
  `v=DMARC1; p=none; rua=mailto:dmarc@sofistes.net`.

Without SPF+DKIM aligned to your From domain, reset emails will usually
land in spam or be rejected. If you ever relay on port 25 directly
(not recommended), you also need a matching **PTR/rDNS** record.

---

## 6. Firewall / ports

- **Outbound 587** to the smarthost must be open:
  ```bash
  sudo ufw allow out 587/tcp
  ```
- You do **not** need to open port 25 inbound; Postfix listens only on
  loopback (step 2), so it is not reachable from the internet.

---

## 7. Wire the suomisf backend to Postfix

The app connects to the local Postfix; Postfix does the real relaying, so
the app config is minimal. Planned `MAIL_*` config in `app/config.py`:

```python
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 25))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', '') == 'true'  # off locally
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')  # unset for local Postfix
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
MAIL_FROM = os.environ.get('MAIL_FROM', 'noreply@sofistes.net')
```

`send_email()` (stdlib `smtplib`) then just does
`smtplib.SMTP('localhost', 25)` and `sendmail(...)`. No auth/TLS needed
for the local hop because Postfix only trusts localhost and handles the
authenticated TLS leg to the smarthost.

> Alternative without Postfix: point `MAIL_*` **directly** at the
> provider (`MAIL_SERVER=smtp.provider.com`, `MAIL_PORT=587`,
> `MAIL_USE_TLS=true`, username/password set). Simpler to start, but then
> every app instance handles auth/TLS/retries itself, and there's no
> local queue if the provider is briefly unreachable. Postfix is the more
> robust production choice.

---

## 8. Security checklist

- `inet_interfaces = loopback-only` and `mynetworks` limited to
  localhost — prevents an open relay.
- `sasl_passwd` and `.db` are `chmod 600`, root-owned.
- Provider credentials live only in `sasl_passwd` (and/or the app's
  environment) — never commit them.
- Use a dedicated From address (`noreply@sofistes.net`).
- Consider a per-IP/route rate limit on the `forgot-password` endpoint so
  the mailer can't be abused to spam an address.

---

## 9. Quick reference

```bash
sudo systemctl status postfix        # service state
mailq                                # outbound queue
sudo postqueue -f                    # flush the queue now
sudo postmap /etc/postfix/sasl_passwd && sudo systemctl restart postfix
sudo tail -f /var/log/mail.log       # live log
```
