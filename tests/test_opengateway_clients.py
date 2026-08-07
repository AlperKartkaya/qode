from __future__ import annotations

import base64
import json
import unittest

import httpx

from smart_road_safety.integration.opengateway import (
    OpenGatewayClient,
    OpenGatewayError,
)


class OpenGatewayClientContractTest(unittest.IsolatedAsyncioTestCase):
    def _client(self, handler):
        return OpenGatewayClient(
            api_root="https://gateway.example",
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="https://backend.example/api/auth/callback",
            qos_profile="teknofest2026",
            transport=httpx.MockTransport(handler),
        )

    async def test_token_exchange_uses_basic_auth_and_exact_form(self):
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url, "https://gateway.example/oauth2/token")
            expected = base64.b64encode(b"client-id:client-secret").decode("ascii")
            self.assertEqual(request.headers["Authorization"], f"Basic {expected}")
            self.assertEqual(
                dict(httpx.QueryParams(request.content.decode("utf-8"))),
                {
                    "grant_type": "authorization_code",
                    "code": "auth-code",
                    "redirect_uri": "https://backend.example/api/auth/callback",
                },
            )
            return httpx.Response(
                200,
                json={"access_token": "secret-token", "token_type": "Bearer", "expires_in": 60},
            )

        token = await self._client(handler).exchange_code("auth-code")
        self.assertEqual(token.access_token, "secret-token")
        self.assertEqual(token.expires_in, 60)

    async def test_number_verification_sends_e164_and_unique_correlator(self):
        correlators: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                request.url, "https://gateway.example/number-verification/v1/verify"
            )
            self.assertEqual(request.headers["Authorization"], "Bearer access-token")
            correlators.append(request.headers["x-correlator"])
            self.assertEqual(json.loads(request.content), {"phoneNumber": "+905390000020"})
            return httpx.Response(
                200,
                headers={"x-correlator": request.headers["x-correlator"]},
                json={"devicePhoneNumberVerified": True},
            )

        client = self._client(handler)
        first = await client.verify_number("access-token", phone_number="+905390000020")
        second = await client.verify_number("access-token", phone_number="+905390000020")
        self.assertTrue(first.verified)
        self.assertEqual(first.correlator, correlators[0])
        self.assertNotEqual(correlators[0], correlators[1])

    async def test_number_verification_rejects_two_identifiers(self):
        client = self._client(lambda request: httpx.Response(500))
        with self.assertRaises(ValueError):
            await client.verify_number(
                "access-token",
                phone_number="+905390000020",
                hashed_phone_number="a" * 64,
            )

    async def test_qod_uses_organizer_payload_without_device(self):
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                request.url, "https://gateway.example/quality-on-demand/v1/sessions"
            )
            self.assertIn("x-correlator", request.headers)
            self.assertEqual(
                json.loads(request.content),
                {
                    "duration": 60,
                    "applicationServer": {"ipv4Address": "0.0.0.0/0"},
                    "qosProfile": "teknofest2026",
                },
            )
            return httpx.Response(
                201,
                json={"sessionId": "2aa98b3a-5f89-4ccd-80d8-0eae3ec4ec95", "duration": 60, "qosStatus": "REQUESTED"},
            )

        result = await self._client(handler).create_qod_session("access-token", 60)
        self.assertEqual(result.qos_status, "REQUESTED")
        self.assertEqual(result.duration, 60)

    async def test_upstream_error_is_typed_and_does_not_expose_body(self):
        client = self._client(
            lambda request: httpx.Response(
                401,
                json={"status": 401, "code": "UNAUTHENTICATED", "message": "secret detail"},
            )
        )
        with self.assertRaises(OpenGatewayError) as caught:
            await client.verify_number("access-token", phone_number="+905390000020")
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(caught.exception.code, "UNAUTHENTICATED")
        self.assertNotIn("secret detail", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
