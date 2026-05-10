import unittest

from omnimem.redact import detect_secrets, redact, redact_inline


class TestDetectSecrets(unittest.TestCase):
    def test_detects_aws_access_key(self):
        text = "Set AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE for the deploy."
        findings = detect_secrets(text)
        self.assertTrue(any(f["name"] == "aws_access_key" for f in findings))

    def test_detects_github_personal_access_token(self):
        text = "token: ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"
        findings = detect_secrets(text)
        self.assertTrue(any(f["name"] == "github_pat" for f in findings))

    def test_detects_openai_key(self):
        text = "API key: sk-1234567890abcdefghijklmnopqrstuv"
        findings = detect_secrets(text)
        self.assertTrue(any(f["name"] == "openai_key" for f in findings))

    def test_detects_anthropic_key(self):
        text = "key: sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        findings = detect_secrets(text)
        self.assertTrue(any(f["name"] == "anthropic_key" for f in findings))

    def test_detects_private_key_block(self):
        text = (
            "Begin block:\n"
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEowIBAAKCAQEA...\n"
            "-----END RSA PRIVATE KEY-----\n"
            "End."
        )
        findings = detect_secrets(text)
        self.assertTrue(any(f["name"] == "private_key_block" for f in findings))

    def test_detects_jwt_token(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc123def456"
        findings = detect_secrets(text)
        self.assertTrue(any(f["name"] == "jwt_token" for f in findings))

    def test_no_findings_in_clean_prose(self):
        text = "This sentence describes a function and references a class name, no secrets here."
        self.assertEqual(detect_secrets(text), [])

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(detect_secrets(""), [])
        self.assertEqual(detect_secrets(None), [])


class TestRedact(unittest.TestCase):
    def test_replaces_match_with_named_placeholder(self):
        text = "Use ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789 in CI."
        redacted, findings = redact(text)
        self.assertIn("[REDACTED:github_pat]", redacted)
        self.assertNotIn("ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789", redacted)
        self.assertEqual(len(findings), 1)

    def test_handles_multiple_overlapping_secrets(self):
        text = (
            "Tokens: ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789 "
            "and sk-abcdefghijklmnopqrstuvwxyz1234567890XYZ"
        )
        redacted, findings = redact(text)
        self.assertGreaterEqual(len(findings), 2)
        for finding in findings:
            self.assertNotIn(finding["match"], redacted)

    def test_custom_placeholder_overrides_named_form(self):
        text = "Token: ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"
        redacted, _ = redact(text, placeholder="<scrubbed>")
        self.assertIn("<scrubbed>", redacted)
        self.assertNotIn("[REDACTED:", redacted)

    def test_redact_inline_returns_only_text(self):
        text = "key: sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        result = redact_inline(text)
        self.assertNotIn("sk-ant-api03-", result)

    def test_redact_passthrough_when_no_secrets(self):
        text = "All clear here."
        redacted, findings = redact(text)
        self.assertEqual(redacted, text)
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
