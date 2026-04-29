"""Secret redaction for OmniMem.

Provides regex-based detection and redaction of common credential shapes so
agents and pipelines can safely ingest content without leaking secrets into
the vault or the vector DB.

This is a *defense-in-depth* layer, not a substitute for keeping secrets out
of source / docs in the first place. Patterns are scoped to high-precision
shapes (provider tokens that follow a public format) to minimize false
positives.
"""

import re

REDACTED_PLACEHOLDER = "[REDACTED]"


# Each pattern is (name, compiled regex). The matching span is replaced with
# `[REDACTED:<name>]`. Patterns are intentionally specific to avoid eating
# legitimate identifiers.
_PATTERNS = [
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("aws_secret_key", re.compile(r"(?<![A-Za-z0-9/])[A-Za-z0-9/+]{40}(?![A-Za-z0-9/+=])")),
    ("github_pat", re.compile(r"\bghp_[A-Za-z0-9]{36,}\b")),
    ("github_oauth", re.compile(r"\bgho_[A-Za-z0-9]{36,}\b")),
    ("github_user_token", re.compile(r"\bghu_[A-Za-z0-9]{36,}\b")),
    ("github_server_token", re.compile(r"\bghs_[A-Za-z0-9]{36,}\b")),
    ("github_refresh_token", re.compile(r"\bghr_[A-Za-z0-9]{36,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{40,}\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("stripe_secret", re.compile(r"\bsk_(?:test|live)_[A-Za-z0-9]{16,}\b")),
    (
        "private_key_block",
        re.compile(
            r"-----BEGIN (?:RSA |OPENSSH |EC |PGP |DSA )?PRIVATE KEY-----.*?-----END (?:RSA |OPENSSH |EC |PGP |DSA )?PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
    (
        "jwt_token",
        re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    ),
    (
        "generic_high_entropy_assignment",
        re.compile(
            r"(?i)(?:password|secret|api[_-]?key|token)\s*[:=]\s*['\"]([^'\"]{16,})['\"]"
        ),
    ),
]


def detect_secrets(text):
    """Return a list of detected secrets without mutating the input.

    Each item is `{name, span: (start, end), match: <substring>}`. Useful for
    audits / dry-runs.
    """
    if not text:
        return []
    findings = []
    for name, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            findings.append(
                {
                    "name": name,
                    "span": (match.start(), match.end()),
                    "match": match.group(0),
                }
            )
    findings.sort(key=lambda item: item["span"][0])
    return findings


def redact(text, placeholder=None):
    """Return the text with every detected secret replaced by a placeholder.

    The placeholder is `[REDACTED:<pattern_name>]` by default so the caller can
    still tell what kind of secret was scrubbed. Pass a string to `placeholder`
    to override (every match uses the same string).
    """
    if not text:
        return text, []

    findings = detect_secrets(text)
    if not findings:
        return text, []

    # Apply replacements right-to-left so earlier spans are not invalidated
    # by later ones.
    output = text
    for finding in sorted(findings, key=lambda item: item["span"][0], reverse=True):
        start, end = finding["span"]
        replacement = placeholder if placeholder is not None else f"[REDACTED:{finding['name']}]"
        output = output[:start] + replacement + output[end:]
    return output, findings


def redact_inline(text, placeholder=None):
    """Convenience wrapper that returns just the redacted text."""
    redacted, _ = redact(text, placeholder=placeholder)
    return redacted
