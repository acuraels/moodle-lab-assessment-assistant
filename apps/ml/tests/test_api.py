import unittest

import httpx

from ml_service.config import Settings
from ml_service.main import create_app
from ml_service.pipeline import Evaluator
from test_pipeline import REPORT, extractor, grounded_result, metadata, response, result


class APITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.model_client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response(result())), base_url="http://ollama")
        settings = Settings(_env_file=None, ml_token="test-only-token")
        evaluator = Evaluator(settings, client=self.model_client, extractor=extractor)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(settings, evaluator)), base_url="http://ml")
        self.headers = {"X-ML-Token": "test-only-token"}

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.model_client.aclose()

    async def test_multipart_success_and_auth(self):
        files = {"submission": ("lab.pdf", b"report", "application/pdf")}
        unauthorized = await self.client.post("/evaluate", data={"metadata": metadata().model_dump_json()}, files=files)
        self.assertEqual(unauthorized.status_code, 401)
        actual = await self.client.post("/evaluate", data={"metadata": metadata().model_dump_json()}, files=files, headers=self.headers)
        self.assertEqual(actual.status_code, 200, actual.text)
        self.assertIsNone(actual.json()["score"])

    async def test_numeric_multipart_returns_grounded_public_contract_in_one_call(self):
        calls = []
        def handler(request):
            calls.append(request)
            return response(grounded_result(score=10, verdict="met", comment="Критерий выполнен."))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ollama") as model_client:
            settings = Settings(_env_file=None, ml_token="test-only-token")
            evaluator = Evaluator(settings, client=model_client, extractor=extractor)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(settings, evaluator)), base_url="http://ml") as client:
                actual = await client.post("/evaluate", data={"metadata": metadata(True).model_dump_json()},
                                           files={"submission": ("lab.pdf", REPORT.encode(), "application/pdf")}, headers=self.headers)
        self.assertEqual(actual.status_code, 200, actual.text)
        self.assertEqual(len(calls), 1)
        payload = actual.json()
        self.assertEqual(set(payload), {"score", "max_score", "conclusion", "criteria"})
        self.assertEqual(payload["score"], 10)
        self.assertEqual(payload["max_score"], 10)
        criterion = payload["criteria"][0]
        self.assertEqual(set(criterion), {"name", "score", "max_score", "comment"})
        self.assertEqual(criterion["name"], "Алгоритм")
        self.assertIn("Источник", criterion["comment"])

    async def test_unreferenced_file_rejected(self):
        actual = await self.client.post("/evaluate", data={"metadata": metadata().model_dump_json()},
                                       files={"submission": ("lab.pdf", b"report", "application/pdf"), "reference_work": ("other.txt", b"secret", "text/plain")}, headers=self.headers)
        self.assertEqual(actual.status_code, 400)

    async def test_invalid_metadata_does_not_echo_data(self):
        actual = await self.client.post("/evaluate", data={"metadata": '{"private":"student-secret"}'},
                                       files={"submission": ("lab.pdf", b"report", "application/pdf")}, headers=self.headers)
        self.assertEqual(actual.status_code, 400)
        self.assertNotIn("student-secret", actual.text)

    async def test_txt_submission_rejected(self):
        actual = await self.client.post("/evaluate", data={"metadata": metadata().model_dump_json()},
                                       files={"submission": ("lab.txt", b"report", "text/plain")}, headers=self.headers)
        self.assertEqual(actual.status_code, 415)

    async def test_health_does_not_need_model(self):
        actual = await self.client.get("/health")
        self.assertEqual(actual.status_code, 200)

    async def test_malformed_and_incomplete_multipart(self):
        for body in (b"not multipart!", b"--x\r\nMalformed header\r\n\r\nvalue\r\n--x--\r\n", b"--x\r\nContent-Disposition: form-data; name=metadata\r\n\r\n{}"):
            actual = await self.client.post("/evaluate", content=body, headers={**self.headers, "Content-Type": "multipart/form-data; boundary=x"})
            self.assertEqual(actual.status_code, 400, actual.text)
            self.assertEqual(actual.json()["error"]["code"], "INVALID_REQUEST")

    async def test_non_ascii_token_is_unauthorized(self):
        actual = await self.client.post("/evaluate", content=b"", headers=[(b"X-ML-Token", b"\xff")])
        self.assertEqual(actual.status_code, 401)
