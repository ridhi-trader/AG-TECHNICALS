"""Outgoing mail for AG Technicals.

Primary: Zoho ZeptoMail (Zoho CPaaS) HTTP API. Fallback: Brevo HTTP API.
Both use port 443 (raw SMTP is blocked on Railway).

Railway env vars:
  ZEPTOMAIL_TOKEN  - "Send Mail Token" of the ZeptoMail agent (with or without the
                     "Zoho-enczapikey " prefix)
  ZEPTOMAIL_HOST   - API host, default api.zeptomail.in (India data centre)
  ZEPTOMAIL_FROM   - default From address on the verified domain (noreply@agtechnicals.com)
  BREVO_API_KEY    - optional fallback
"""
import json
import os
import urllib.error
import urllib.request

DEFAULT_FROM = "noreply@agtechnicals.com"


def _zepto_token():
    t = (os.environ.get("ZEPTOMAIL_TOKEN") or "").strip()
    if not t:
        return ""
    return t if t.lower().startswith("zoho-enczapikey") else "Zoho-enczapikey " + t


def _post(url, headers, payload, timeout):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            detail = ""
        raise RuntimeError(f"HTTP {e.code} {detail}")


def _send_zepto(to_email, subject, html, sender_name, sender_email, reply_to, timeout):
    host = (os.environ.get("ZEPTOMAIL_HOST") or "api.zeptomail.in").strip()
    payload = {
        "from": {"address": sender_email, "name": sender_name},
        "to": [{"email_address": {"address": to_email}}],
        "subject": subject,
        "htmlbody": html,
    }
    if reply_to:
        payload["reply_to"] = [{"address": reply_to, "name": sender_name}]
    _post(f"https://{host}/v1.1/email",
          {"accept": "application/json", "content-type": "application/json",
           "authorization": _zepto_token()}, payload, timeout)


def _send_brevo(to_email, subject, html, sender_name, sender_email, reply_to, timeout):
    key = (os.environ.get("BREVO_API_KEY") or "").strip()
    payload = {
        "sender": {"name": sender_name,
                   "email": os.environ.get("GMAIL_USER") or "candleagtechnical456@gmail.com"},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html,
    }
    if reply_to:
        payload["replyTo"] = {"email": reply_to}
    _post("https://api.brevo.com/v3/smtp/email",
          {"accept": "application/json", "content-type": "application/json", "api-key": key},
          payload, timeout)


def send_mail(to_email, subject, html, sender_name="AG Technicals", sender_email=None,
              reply_to=None, timeout=12):
    """Send one email. Tries ZeptoMail, then Brevo. Raises if every configured provider fails."""
    sender_email = sender_email or os.environ.get("ZEPTOMAIL_FROM") or DEFAULT_FROM
    errors = []
    if _zepto_token():
        try:
            _send_zepto(to_email, subject, html, sender_name, sender_email, reply_to, timeout)
            return "zeptomail"
        except Exception as e:
            print(f"ZeptoMail error: {e}")
            errors.append(f"zeptomail: {e}")
    if (os.environ.get("BREVO_API_KEY") or "").strip():
        try:
            _send_brevo(to_email, subject, html, sender_name, sender_email, reply_to, timeout)
            return "brevo"
        except Exception as e:
            print(f"Brevo email error: {e}")
            errors.append(f"brevo: {e}")
    if not errors:
        raise RuntimeError("No email provider configured (set ZEPTOMAIL_TOKEN in Railway variables)")
    raise RuntimeError("; ".join(errors))


def provider_status():
    if _zepto_token():
        return "zeptomail"
    if (os.environ.get("BREVO_API_KEY") or "").strip():
        return "brevo"
    return "not_configured"
