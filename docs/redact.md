# OmniMem Secret Redaction

`omnimem redact` scans text for common credential shapes and replaces them with named placeholders. It's a defense-in-depth layer for pipelines that ingest content into the OmniMem vault: keep secrets out of source in the first place, but redact as a safety net.

## Patterns covered

| Pattern | Example shape |
|---|---|
| `aws_access_key` | `AKIA...` / `ASIA...` (20 chars) |
| `aws_secret_key` | 40-char base64-ish secret following an access key |
| `github_pat` | `ghp_...` (40+ chars) |
| `github_oauth` / `github_user_token` / `github_server_token` / `github_refresh_token` | `gho_...`, `ghu_...`, `ghs_...`, `ghr_...` |
| `openai_key` | `sk-...` (20+ chars) |
| `anthropic_key` | `sk-ant-...` |
| `slack_token` | `xoxb-...`, `xoxa-...`, etc. |
| `google_api_key` | `AIza...` (39 chars) |
| `stripe_secret` | `sk_test_...`, `sk_live_...` |
| `private_key_block` | full PEM blocks (RSA / OPENSSH / EC / PGP / DSA) |
| `jwt_token` | `eyJ....eyJ....` three-part tokens |
| `generic_high_entropy_assignment` | `password = "..."`, `api_key: "..."` with 16+ char value |

Patterns are scoped to high-precision shapes (provider tokens follow public formats) to keep false positives low. Generic high-entropy strings without a key/value cue are NOT redacted.

## CLI

### Detect only

```bash
echo "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE" | omnimem redact - --detect-only --json
```

Returns the list of findings (name, span, match) without modifying the input.

### Redact

```bash
echo "token: ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789" | omnimem redact - --json
```

Returns the redacted text and a list of findings. Each match is replaced by `[REDACTED:<pattern_name>]`.

## Library use

```python
from omnimem.redact import detect_secrets, redact, redact_inline

findings = detect_secrets(text)
redacted, findings = redact(text)
clean = redact_inline(text, placeholder="<scrubbed>")
```

## When to apply

- Before `omnimem add` / `omnimem import` if the content originates from an untrusted source. Pipe through `redact -` first.
- Inside automation that exports notes from external systems (chat transcripts, logs).
- As a `pre-commit` step when authoring notes by hand.

The library doesn't auto-redact during ingest — opt-in is intentional so you can audit findings before mutation. Future releases may add an opt-in `--redact` flag on `add` / `import`.
