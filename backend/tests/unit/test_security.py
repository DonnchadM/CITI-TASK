"""Unit tests: PBKDF2 password hashing (auth service)."""


def test_hash_verify_roundtrip(loader):
    security = loader("auth", "security")
    hashed = security.hash_password("s3cret-pass")
    assert hashed != "s3cret-pass"
    assert hashed.startswith("pbkdf2_sha256$")
    assert security.verify_password("s3cret-pass", hashed) is True


def test_wrong_password_rejected(loader):
    security = loader("auth", "security")
    hashed = security.hash_password("correct")
    assert security.verify_password("wrong", hashed) is False


def test_malformed_hash_is_false_not_exception(loader):
    security = loader("auth", "security")
    assert security.verify_password("anything", "garbage") is False
    assert security.verify_password("anything", "") is False


def test_salt_makes_hashes_unique(loader):
    security = loader("auth", "security")
    a = security.hash_password("same")
    b = security.hash_password("same")
    assert a != b  # different random salt each time
    assert security.verify_password("same", a) and security.verify_password("same", b)
