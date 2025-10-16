"""Unit tests for password hashing utilities."""

import pytest

from backend.app.core.security.password import (
    hash_password,
    needs_rehash,
    verify_password,
)


class TestHashPassword:
    """Tests for hash_password function."""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_returns_argon2_hash(self):
        """Test that hash_password returns an Argon2 hash."""
        password = "test_password_123"
        hashed = hash_password(password)

        # Argon2 hashes start with $argon2
        assert hashed.startswith("$argon2")

    def test_hash_password_different_for_same_input(self):
        """Test that hashing the same password twice produces different hashes."""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2

    def test_hash_password_with_empty_string(self):
        """Test hashing an empty string."""
        password = ""
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert hashed.startswith("$argon2")

    def test_hash_password_with_special_characters(self):
        """Test hashing password with special characters."""
        password = "p@ssw0rd!#$%^&*()"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert hashed.startswith("$argon2")

    def test_hash_password_with_unicode(self):
        """Test hashing password with unicode characters."""
        password = "senha_çãõáéí_🔒"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert hashed.startswith("$argon2")

    def test_hash_password_with_long_password(self):
        """Test hashing a very long password."""
        password = "a" * 1000  # 1000 character password
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert hashed.startswith("$argon2")


class TestVerifyPassword:
    """Tests for verify_password function."""

    def test_verify_password_correct(self):
        """Test verifying a correct password."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying an incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password_456"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "TestPassword123"
        wrong_case = "testpassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password(wrong_case, hashed) is False

    def test_verify_password_empty_string(self):
        """Test verifying an empty string password."""
        password = ""
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("nonempty", hashed) is False

    def test_verify_password_with_special_characters(self):
        """Test verifying password with special characters."""
        password = "p@ssw0rd!#$%^&*()"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("p@ssw0rd!#$%^&*()x", hashed) is False

    def test_verify_password_with_unicode(self):
        """Test verifying password with unicode characters."""
        password = "senha_çãõáéí_🔒"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("senha_çãõáéí_🔓", hashed) is False

    def test_verify_password_with_invalid_hash(self):
        """Test verifying password with invalid hash format."""
        password = "test_password_123"
        invalid_hash = "not_a_valid_argon2_hash"

        with pytest.raises(ValueError):
            verify_password(password, invalid_hash)

    def test_verify_password_timing_attack_resistance(self):
        """Test that verification time is consistent regardless of correctness."""
        import time

        password = "test_password_123"
        hashed = hash_password(password)

        # Measure time for correct password
        start = time.perf_counter()
        verify_password(password, hashed)
        correct_time = time.perf_counter() - start

        # Measure time for incorrect password
        start = time.perf_counter()
        verify_password("wrong_password", hashed)
        incorrect_time = time.perf_counter() - start

        # Times should be similar (within 50% of each other)
        # This is a weak check but sufficient for unit testing
        # Real timing attack resistance is handled by Argon2 implementation
        ratio = max(correct_time, incorrect_time) / min(correct_time, incorrect_time)
        assert ratio < 2.0  # Allow up to 2x difference


class TestNeedsRehash:
    """Tests for needs_rehash function."""

    def test_needs_rehash_new_hash(self):
        """Test that a newly created hash doesn't need rehashing."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert needs_rehash(hashed) is False

    def test_needs_rehash_with_invalid_hash(self):
        """Test needs_rehash with invalid hash format."""
        invalid_hash = "not_a_valid_argon2_hash"

        with pytest.raises(ValueError):
            needs_rehash(invalid_hash)

    def test_needs_rehash_empty_string(self):
        """Test needs_rehash with empty string."""
        with pytest.raises(ValueError):
            needs_rehash("")


class TestPasswordIntegration:
    """Integration tests for password hashing workflow."""

    def test_complete_password_workflow(self):
        """Test complete password hashing and verification workflow."""
        # User registration
        plain_password = "user_password_123"
        hashed_password = hash_password(plain_password)

        # Store hashed_password in database (simulated)
        assert hashed_password.startswith("$argon2")

        # User login - correct password
        login_password = "user_password_123"
        assert verify_password(login_password, hashed_password) is True

        # User login - incorrect password
        wrong_password = "wrong_password_456"
        assert verify_password(wrong_password, hashed_password) is False

        # Check if rehash needed (should be False for new hash)
        assert needs_rehash(hashed_password) is False

    def test_multiple_users_same_password(self):
        """Test that multiple users with same password get different hashes."""
        password = "common_password"

        user1_hash = hash_password(password)
        user2_hash = hash_password(password)
        user3_hash = hash_password(password)

        # All hashes should be different
        assert user1_hash != user2_hash
        assert user2_hash != user3_hash
        assert user1_hash != user3_hash

        # But all should verify correctly
        assert verify_password(password, user1_hash) is True
        assert verify_password(password, user2_hash) is True
        assert verify_password(password, user3_hash) is True

    def test_password_change_workflow(self):
        """Test password change workflow."""
        # Original password
        old_password = "old_password_123"
        old_hash = hash_password(old_password)

        # Verify old password works
        assert verify_password(old_password, old_hash) is True

        # Change password
        new_password = "new_password_456"
        new_hash = hash_password(new_password)

        # Old password shouldn't work with new hash
        assert verify_password(old_password, new_hash) is False

        # New password should work with new hash
        assert verify_password(new_password, new_hash) is True

        # New password shouldn't work with old hash
        assert verify_password(new_password, old_hash) is False
