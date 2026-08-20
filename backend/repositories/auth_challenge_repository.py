"""Emailed secrets: verify-email links, password-reset links, and login OTPs.

One table, three purposes. Every secret is stored only as a SHA-256 hash — the
raw token or code is emailed and never persisted, so reading the database cannot
reconstruct a live link or code. Each row is single-use (``consumed_at``),
time-bounded (``expires_at``), and — for the OTP — attempt-capped.

Issuing a new challenge of a purpose invalidates any earlier unconsumed one of
the same purpose for that student, so only the most recent link/code works. That
is what makes "resend" safe: the old mail's secret stops working the moment a
new one is sent.
"""

import hashlib
from typing import Any, Optional, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from config.database import db


def hash_secret(raw: str) -> str:
    """The stored form of a token or code. SHA-256 is right here: the secret is
    already high-entropy (a long random token, or a code with a short life and a
    hard attempt cap), so a slow password hash buys nothing."""
    return hashlib.sha256(raw.encode()).hexdigest()


class AuthChallengeRepository:
    @staticmethod
    def issue(student_id, purpose: str, raw_secret: str, ttl_seconds: int) -> None:
        """Store a new challenge, invalidating prior unconsumed ones of the same
        purpose. Does its own commit — a challenge with no committed row would be
        a link that never works.
        """
        db.session.execute(
            text("""
                UPDATE auth_email_challenges
                SET consumed_at = CURRENT_TIMESTAMP
                WHERE student_id = :student_id
                  AND purpose = :purpose
                  AND consumed_at IS NULL
            """),
            {"student_id": student_id, "purpose": purpose},
        )
        db.session.execute(
            text("""
                INSERT INTO auth_email_challenges (
                    student_id, purpose, secret_hash, expires_at
                ) VALUES (
                    :student_id, :purpose, :secret_hash,
                    CURRENT_TIMESTAMP + (:ttl || ' seconds')::interval
                )
            """),
            {
                "student_id": student_id,
                "purpose": purpose,
                "secret_hash": hash_secret(raw_secret),
                "ttl": str(int(ttl_seconds)),
            },
        )
        db.session.commit()

    @staticmethod
    def seconds_since_last(student_id, purpose: str) -> Optional[int]:
        """How long since the most recent challenge of this purpose was issued,
        or None if there has never been one. Used to rate-limit resends."""
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                SELECT FLOOR(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - MAX(created_at))))::int
                FROM auth_email_challenges
                WHERE student_id = :student_id AND purpose = :purpose
            """),
            {"student_id": student_id, "purpose": purpose},
        ))
        value = result.scalar()
        return int(value) if value is not None else None

    @staticmethod
    def consume_by_token(purpose: str, raw_secret: str):
        """For link flows: find a live challenge by its token hash and consume it
        atomically. Returns the student_id on success, or None if the token is
        unknown, already used, or expired.

        The UPDATE ... WHERE ... RETURNING does the check and the consume in one
        statement, so a token cannot be redeemed twice by two concurrent clicks.
        """
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                UPDATE auth_email_challenges
                SET consumed_at = CURRENT_TIMESTAMP
                WHERE secret_hash = :secret_hash
                  AND purpose = :purpose
                  AND consumed_at IS NULL
                  AND expires_at > CURRENT_TIMESTAMP
                RETURNING student_id
            """),
            {"secret_hash": hash_secret(raw_secret), "purpose": purpose},
        ))
        row = result.mappings().first()
        db.session.commit()
        return row["student_id"] if row else None

    @staticmethod
    def verify_otp(student_id, raw_code: str, max_attempts: int = 5) -> bool:
        """For the OTP flow: check the code against this student's latest live
        login OTP, consuming it on success and counting the guess either way.

        Returns True only on a correct, unexpired, unconsumed code with attempts
        left. A wrong guess increments attempts; once the cap is hit the code is
        consumed so it cannot be brute-forced further.
        """
        result = cast(CursorResult[Any], db.session.execute(
            text("""
                SELECT challenge_id, secret_hash, attempts
                FROM auth_email_challenges
                WHERE student_id = :student_id
                  AND purpose = 'login_otp'
                  AND consumed_at IS NULL
                  AND expires_at > CURRENT_TIMESTAMP
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"student_id": student_id},
        ))
        row = result.mappings().first()

        if row is None:
            return False

        if row["attempts"] >= max_attempts:
            # Out of guesses: burn it so it can never succeed later.
            db.session.execute(
                text("UPDATE auth_email_challenges SET consumed_at = CURRENT_TIMESTAMP "
                     "WHERE challenge_id = :id"),
                {"id": row["challenge_id"]},
            )
            db.session.commit()
            return False

        if row["secret_hash"] == hash_secret(raw_code):
            db.session.execute(
                text("UPDATE auth_email_challenges SET consumed_at = CURRENT_TIMESTAMP "
                     "WHERE challenge_id = :id"),
                {"id": row["challenge_id"]},
            )
            db.session.commit()
            return True

        db.session.execute(
            text("UPDATE auth_email_challenges SET attempts = attempts + 1 "
                 "WHERE challenge_id = :id"),
            {"id": row["challenge_id"]},
        )
        db.session.commit()
        return False
