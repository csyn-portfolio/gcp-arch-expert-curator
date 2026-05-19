from unittest.mock import MagicMock, patch

import pytest

from curator.github_app import GitHubApp, _build_jwt

# 2048-bit RSA test key — for unit tests only; never used in production.
TEST_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCouM/P1DPPfFli
XJ/sW1a1DE2ZpEsVjj3GvBaJ66ZBcfrSQxd6Sp8JRJt6JEAfzEOejZJ57y9hKt6d
J8vHy/XWsDefXySwm0pgAMzv4Z9NvuBd/zbyhMFze9qJ0sihkBK7zlhWQapbaSne
5ZFTT2CAWa5LSf1SKH+R3mcYKUipxhO+jYdtbeEAqezhAxjMc5dRxNODD2L4oiwD
JvRwM02aP6eYMZ9ynrpZHqQxnX7QSsyYrS9i0J9D2jGeeI6f8jSGwBxQdUQJ2YMJ
mi9KjM7+pY+6qNYDU3gchQedtrgXEZ0mtvg8Y7BFDwar7G0eVZZYye4Ifk1Ckxb1
5OaCUqUrAgMBAAECggEABSLTGKWCCj/jzK27JIvHQO2l8xZgPsC8uq8BFKO6xOU+
WGY4cb2Rx8tx3C78ULt8F3iBy/pu+8s9SZVri6J20lk86DoSONoRUojTtD2vBsPX
uqTJPGq0JNrRVT64Ysqq91KZt8557BxwbNuaJ+oTqvSP7LTM5FJdR8h4ZPDkyF41
ig+Q/kPwUUID9xTChymB+jS7u6kJCDVqkaOppGP3mruai4Ej19b10TYLjN+rye+d
q8n2vZXnpuPXfc8vXvv45A2582++tJoHllI8kXI8azPTLfIrbDoGYCGQSaeik0pX
EfAkguOJtXL19zE++CCcJCG/W+RtZjV9a/6Gkw+AKQKBgQDi0a2hKndXxYyeIsjs
eW43Ikntc35MPcykoz78us/4zpqbN/Uy2krVcERvd9PP7EK7y4VcElGeZ/lKArNt
MgA948AvuPMVrcCqdPONqmCvplS+cJOk7cvQNOdEg2MtJ9mpjMPG2wCc1cIdXu2J
cyByLgdVIIJtb4lSah5HQuu2zwKBgQC+bbH0JE2XUitk7iBNcOpIOelDK9O6DQe7
FK4v5/8dA7G3aeaIcXjEKnEkT6Nbyg8LndofmEXewHucVDVjXVkFY+o8xXyESkth
U1u0yUKYjUfqFa7fa9UVmVkvYKfywWs7z261Skhv09Fp28og9U183q4hnTNFgEkT
yT+OO+2C5QKBgA0aY9dtpptRdEAmbkkK8s0IlBC9nUw2Pb49GARtnloXRWM2Jlob
tjsCU1HFMF1QnsJOjZO2EzT9eK9H3KmwO8dXguC+5HwaH4k5XGCQuSksiLS/uCfM
/Ps4MywIExCmvrJGyYCRYkWtK5uawkowdm1iL1ZBnIdJ7DrwmnMvcIKNAoGANZDf
xOBNXyqDAGInfgEsNeLsZbO3XBd8PDjGAr3MulmmrQRCD9FzeiLCLsekGRbOgqMF
j2ujA9S7MK9TUT8Z4nVHl46pxwCrEZaELmeKryTWvNcamMhZaTj4qGYU+ClGQ83G
w4JAvAwmVRO5WOoHwP9WligFGyDJ7aHnmdfrqK0CgYEAua6uzRmQXZbzlWhtXoY1
wC7QpmXf/ORtUQL+9yxiKCUPX1fgTbz8cBA/QzvhBH/azxqGWCAl9e+JPa4zgRBN
dzeEIAkIB8NN/cpDTfA2vrW1TDbrHKSUXUKUkbBzWxKIWPwOmjoK0F/aLep8btHb
l1l1q/xQ7BrwZ7ANnPAt0z8=
-----END PRIVATE KEY-----"""


def test_build_jwt_includes_app_id_and_short_expiry():
    token = _build_jwt(app_id=123456, private_key_pem=TEST_PRIVATE_KEY, now=1_000_000)
    # Decode without verification — just check claims structurally
    import jwt
    decoded = jwt.decode(token, options={"verify_signature": False})
    assert decoded["iss"] == "123456"
    assert decoded["iat"] == 1_000_000 - 60
    assert decoded["exp"] == 1_000_000 + 540  # 9 minutes


def test_installation_token_calls_correct_endpoint():
    app = GitHubApp(app_id=123456, private_key_pem=TEST_PRIVATE_KEY, installation_id=789)
    fake_response = MagicMock(status_code=201)
    fake_response.json.return_value = {"token": "ghs_test_token", "expires_at": "..."}
    with patch("curator.github_app.httpx.post", return_value=fake_response) as p:
        token = app.installation_token()
    assert token == "ghs_test_token"
    args, kwargs = p.call_args
    assert "/app/installations/789/access_tokens" in args[0]
    assert kwargs["headers"]["Authorization"].startswith("Bearer ")


def test_installation_token_raises_on_401():
    app = GitHubApp(app_id=123456, private_key_pem=TEST_PRIVATE_KEY, installation_id=789)
    fake_response = MagicMock(status_code=401)
    fake_response.text = "Bad credentials"
    with patch("curator.github_app.httpx.post", return_value=fake_response), pytest.raises(
        RuntimeError
    ) as exc:
        app.installation_token()
    assert "rotate" in str(exc.value).lower() or "401" in str(exc.value)
