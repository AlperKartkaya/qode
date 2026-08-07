from __future__ import annotations

import unittest

from smart_road_safety.integration.auth import AuthSessionStore, AuthStateError
from smart_road_safety.integration.opengateway import AccessToken


class AuthSessionStoreTest(unittest.TestCase):
    def test_state_is_one_time_and_token_is_not_in_public_summary(self):
        now = [100.0]
        store = AuthSessionStore(state_ttl_seconds=30, session_ttl_seconds=300, clock=lambda: now[0])
        pending = store.create_pending()
        token = AccessToken(access_token="never-publish", token_type="Bearer", expires_in=60)

        flow = store.complete_authorization(pending.state, token)
        summary = store.public_summary(flow.flow_id)

        self.assertEqual(summary["status"], "AUTHORIZED")
        self.assertNotIn("access_token", summary)
        self.assertNotIn("never-publish", repr(summary))
        with self.assertRaises(AuthStateError):
            store.complete_authorization(pending.state, token)

    def test_expired_state_and_expired_token_fail_closed(self):
        now = [100.0]
        store = AuthSessionStore(state_ttl_seconds=10, session_ttl_seconds=300, clock=lambda: now[0])
        pending = store.create_pending()
        now[0] = 111.0
        with self.assertRaises(AuthStateError):
            store.complete_authorization(
                pending.state,
                AccessToken(access_token="token", token_type="Bearer", expires_in=60),
            )

        pending = store.create_pending()
        flow = store.complete_authorization(
            pending.state,
            AccessToken(access_token="token", token_type="Bearer", expires_in=5),
        )
        now[0] += 6.0
        with self.assertRaises(AuthStateError):
            store.require_access_token(flow.flow_id)


if __name__ == "__main__":
    unittest.main()
