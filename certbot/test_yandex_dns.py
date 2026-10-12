import base64
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import yandex_dns


class YandexDnsHookTest(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "CERTBOT_VALIDATION": "challenge-token",
            "DNS_ZONE_ID": "zone-test",
            "DNS_RECORD_NAME": "_acme-challenge.bi.kitexp.ru.",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    @patch("yandex_dns.time.sleep")
    @patch("yandex_dns.update_record_sets")
    @patch("yandex_dns.challenge_record_sets", return_value=[])
    @patch("yandex_dns.access_token", return_value="mock-iam-token")
    def test_auth_uses_certbot_domain_for_each_san(self, token, records, update, sleep):
        with patch.dict(os.environ, {"CERTBOT_DOMAIN": "secrets.kitexp.ru"}):
            yandex_dns.modify_challenge(remove=False)

        update.assert_called_once_with("mock-iam-token", "zone-test", [{
            "name": "_acme-challenge.secrets.kitexp.ru.",
            "type": "TXT",
            "ttl": "60",
            "data": ['"challenge-token"'],
        }], [])
        sleep.assert_called_once()

    @patch("yandex_dns.time.sleep")
    @patch("yandex_dns.update_record_sets")
    @patch("yandex_dns.challenge_record_sets")
    @patch("yandex_dns.access_token", return_value="mock-iam-token")
    def test_auth_adds_own_value_and_preserves_existing_values(self, token, records, update, sleep):
        records.return_value = [{
            "name": "_acme-challenge.bi.kitexp.ru.",
            "type": "TXT",
            "ttl": "60",
            "data": ['"other-challenge"'],
        }]

        yandex_dns.modify_challenge(remove=False)

        update.assert_called_once_with("mock-iam-token", "zone-test", [{
            "name": "_acme-challenge.bi.kitexp.ru.",
            "type": "TXT",
            "ttl": "60",
            "data": ['"other-challenge"', '"challenge-token"'],
        }], records.return_value)
        sleep.assert_called_once()

    @patch("yandex_dns.update_record_sets")
    @patch("yandex_dns.challenge_record_sets")
    @patch("yandex_dns.access_token", return_value="mock-iam-token")
    def test_cleanup_removes_only_its_value(self, token, records, update):
        records.return_value = [{
            "name": "_acme-challenge.bi.kitexp.ru.",
            "type": "TXT",
            "ttl": "60",
            "data": ['"other-challenge"', '"challenge-token"'],
        }]

        yandex_dns.modify_challenge(remove=True)

        update.assert_called_once_with("mock-iam-token", "zone-test", [{
            "name": "_acme-challenge.bi.kitexp.ru.",
            "type": "TXT",
            "ttl": "60",
            "data": ['"other-challenge"'],
        }], records.return_value)

    @patch("yandex_dns.update_record_sets")
    @patch("yandex_dns.challenge_record_sets", return_value=[])
    @patch("yandex_dns.access_token", return_value="mock-iam-token")
    def test_cleanup_is_idempotent_when_value_is_absent(self, token, records, update):
        yandex_dns.modify_challenge(remove=True)
        update.assert_not_called()

    @patch("yandex_dns.request")
    def test_record_listing_follows_all_pages(self, request):
        request.side_effect = [
            {"recordSets": [], "nextPageToken": "next page"},
            {"recordSets": [{"name": "_acme-challenge.bi.kitexp.ru.", "type": "TXT", "data": ['"x"']}]},
        ]

        records = yandex_dns.challenge_record_sets(
            "token", "zone/test", "_acme-challenge.bi.kitexp.ru."
        )

        self.assertEqual(1, len(records))
        self.assertIn("pageToken=next%20page", request.call_args_list[1].args[0])

    @patch("yandex_dns.request", return_value={"recordSets": [], "nextPageToken": "same-token"})
    def test_record_listing_rejects_repeated_page_token(self, request):
        with self.assertRaisesRegex(RuntimeError, "repeated a record-set page token"):
            yandex_dns.challenge_record_sets("token", "zone", "_acme-challenge.bi.kitexp.ru.")
        self.assertEqual(2, request.call_count)

    @patch("yandex_dns.request", return_value={"iamToken": "issued-token"})
    def test_access_token_builds_ps256_jwt_for_iam_audience(self, request):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()
        with tempfile.TemporaryDirectory() as temporary:
            key_file = Path(temporary) / "key.json"
            key_file.write_text(json.dumps({
                "id": "key-test",
                "service_account_id": "service-account-test",
                "private_key": pem,
            }))
            with patch.dict(os.environ, {
                "YANDEX_SERVICE_ACCOUNT_ID": "service-account-test",
                "YANDEX_KEY_ID": "key-test",
                "YANDEX_SERVICE_ACCOUNT_KEY_FILE": str(key_file),
            }):
                self.assertEqual("issued-token", yandex_dns.access_token())

        jwt = request.call_args.kwargs["body"]["jwt"]
        header_text, payload_text, _ = jwt.split(".")
        decode = lambda value: json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))
        self.assertEqual({"alg": "PS256", "kid": "key-test", "typ": "JWT"}, decode(header_text))
        self.assertEqual(yandex_dns.IAM_API, decode(payload_text)["aud"])
        self.assertEqual("service-account-test", decode(payload_text)["iss"])

    def test_service_account_key_validation_rejects_placeholder_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            key_file = Path(temporary) / "key.json"
            key_file.write_text("{}")
            with patch.dict(os.environ, {
                "YANDEX_SERVICE_ACCOUNT_ID": "service-account-test",
                "YANDEX_KEY_ID": "key-test",
                "YANDEX_SERVICE_ACCOUNT_KEY_FILE": str(key_file),
            }):
                with self.assertRaisesRegex(RuntimeError, "key id does not match"):
                    yandex_dns.service_account_private_key()

    @patch("yandex_dns.time.monotonic", side_effect=[0, 0, 0.1, 0.2])
    @patch("yandex_dns.time.sleep")
    @patch("yandex_dns.request")
    def test_update_polls_operation_with_bounded_timeout(self, request, sleep, monotonic):
        request.side_effect = [{"id": "operation/test"}, {"done": True}]

        yandex_dns.update_record_sets("token", "zone", [], [])

        sleep.assert_called_once_with(1)
        self.assertEqual(20, request.call_args_list[1].kwargs["timeout"])
        self.assertTrue(request.call_args_list[1].args[0].endswith("/operation%2Ftest"))

    @patch("yandex_dns.time.monotonic", side_effect=[0, 61])
    @patch("yandex_dns.request", return_value={"id": "operation-test"})
    def test_update_times_out_at_global_deadline(self, request, monotonic):
        with self.assertRaisesRegex(RuntimeError, "did not finish within 60 seconds"):
            yandex_dns.update_record_sets("token", "zone", [], [])

    @patch("yandex_dns.time.monotonic", return_value=0)
    @patch("yandex_dns.request", return_value={
        "id": "operation-test", "done": True, "error": {"message": "denied"}
    })
    def test_update_surfaces_operation_error(self, request, monotonic):
        with self.assertRaisesRegex(RuntimeError, "denied"):
            yandex_dns.update_record_sets("token", "zone", [], [])

    def test_request_surfaces_http_error_body(self):
        error = urllib.error.HTTPError(
            "https://example.test", 403, "Forbidden", {}, io.BytesIO(b"denied by policy")
        )
        with patch("yandex_dns.urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "HTTP 403: denied by policy"):
                yandex_dns.request("https://example.test")


if __name__ == "__main__":
    unittest.main()
