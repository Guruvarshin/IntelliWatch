"""Phase 8.5: digest email formatting and sending via Resend.

Sends both an HTML version (styled, for normal email clients) and a
plain-text version (fallback for clients that don't render HTML, and for
spam filters that prefer multipart emails). Resend, like virtually every
provider, accepts both in one call and lets the client choose.
"""

import html as html_module
import os

import httpx
import markdown as md

RESEND_API_URL = "https://api.resend.com/emails"

# Inline-friendly CSS: a <style> block in <head> is supported by Gmail,
# Apple Mail, Outlook web/desktop, and most modern clients. Keeping styles
# class-based (rather than inlining every tag) keeps _markdown_to_html simple
# -- the markdown library just needs to emit normal h2/h3/ul/li/strong/code,
# and the <style> block handles appearance.
_STYLE = """
  body { margin: 0; padding: 0; background-color: #f4f5f7; }
  .wrapper { width: 100%; padding: 24px 0; background-color: #f4f5f7; }
  .container {
    max-width: 600px; margin: 0 auto; background-color: #ffffff;
    border-radius: 12px; overflow: hidden;
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1f2937;
  }
  .header { background-color: #111827; padding: 28px 32px; }
  .header h1 { margin: 0; color: #ffffff; font-size: 20px; letter-spacing: 0.02em; }
  .header p { margin: 6px 0 0; color: #9ca3af; font-size: 13px; }
  .body { padding: 8px 32px 24px; }
  .competitor { margin-top: 24px; padding-top: 20px; border-top: 1px solid #e5e7eb; }
  .competitor:first-child { margin-top: 16px; padding-top: 0; border-top: none; }
  .competitor h2 {
    margin: 0 0 12px; font-size: 17px; color: #111827;
    display: inline-block; padding: 4px 10px; background-color: #eef2ff;
    border-radius: 6px;
  }
  .competitor h3 { font-size: 14px; color: #374151; margin: 16px 0 6px; }
  .competitor p { font-size: 14px; line-height: 1.6; margin: 8px 0; }
  .competitor ul { margin: 8px 0; padding-left: 20px; }
  .competitor li { font-size: 14px; line-height: 1.6; margin: 4px 0; }
  .competitor strong { color: #111827; }
  .competitor code {
    background-color: #f3f4f6; padding: 1px 5px; border-radius: 4px;
    font-size: 13px;
  }
  .footer {
    padding: 16px 32px; background-color: #f9fafb; color: #9ca3af;
    font-size: 12px; text-align: center;
  }
"""

_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>{style}</style>
  </head>
  <body>
    <div class="wrapper">
      <div class="container">
        <div class="header">
          <h1>IntelliWatch</h1>
          <p>Weekly Competitive Intelligence Digest</p>
        </div>
        <div class="body">
          {sections}
        </div>
        <div class="footer">
          You're tracking {count} competitor{plural} on IntelliWatch.
        </div>
      </div>
    </div>
  </body>
</html>
"""


def _markdown_to_html(text: str) -> str:
    return md.markdown(text)


def format_digest_email(briefs: list[dict]) -> tuple[str, str, str]:
    """briefs: list of {"name": competitor name, "content": brief markdown}.
    Returns (subject, html_body, text_body)."""
    count = len(briefs)
    subject = f"IntelliWatch Weekly Digest ({count} competitor{'s' if count != 1 else ''})"

    text_sections = []
    html_sections = []
    for b in briefs:
        name = html_module.escape(b["name"])
        text_sections.append(f"{b['name']}\n{'=' * len(b['name'])}\n\n{b['content']}")
        html_sections.append(
            f'<div class="competitor"><h2>{name}</h2>{_markdown_to_html(b["content"])}</div>'
        )

    text_body = "\n\n---\n\n".join(text_sections)
    html_body = _HTML_TEMPLATE.format(
        style=_STYLE,
        sections="\n".join(html_sections),
        count=count,
        plural="s" if count != 1 else "",
    )
    return subject, html_body, text_body


async def send_email(to: str, subject: str, html_body: str, text_body: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"},
            json={
                "from": os.environ["RESEND_FROM_EMAIL"],
                "to": [to],
                "subject": subject,
                "html": html_body,
                "text": text_body,
            },
        )
        resp.raise_for_status()
