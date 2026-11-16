import unittest
from unittest.mock import AsyncMock, Mock, patch

import aiohttp

from github_stats import Queries


class RestQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_content_does_not_retry_or_use_fallback(self):
        response = Mock(status=204)
        response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(
            request_info=Mock(real_url='https://api.github.com'), history=()))
        session = Mock()
        session.get = AsyncMock(return_value=response)
        queries = Queries('user', 'token', session)
        with patch('github_stats.requests.get') as fallback:
            result = await queries.query_rest('/repos/example/repo/stats/contributors')
        self.assertEqual(result, {})
        self.assertEqual(session.get.await_count, 1)
        fallback.assert_not_called()

    async def test_accepted_response_is_retried(self):
        pending = Mock(status=202)
        ready = Mock(status=200)
        ready.json = AsyncMock(return_value=[{'total': 1}])
        session = Mock()
        session.get = AsyncMock(side_effect=[pending, ready])
        queries = Queries('user', 'token', session)
        with patch('github_stats.asyncio.sleep', new_callable=AsyncMock) as sleep:
            result = await queries.query_rest('/repos/example/repo/stats/contributors')
        self.assertEqual(result, [{'total': 1}])
        sleep.assert_awaited_once_with(2)

    async def test_fallback_no_content_does_not_retry(self):
        session = Mock()
        session.get = AsyncMock(side_effect=aiohttp.ClientConnectionError())
        queries = Queries('user', 'token', session)
        with patch('github_stats.requests.get', return_value=Mock(status_code=204)) as fallback:
            result = await queries.query_rest('/repos/example/repo/stats/contributors')
        self.assertEqual(result, {})
        self.assertEqual(session.get.await_count, 1)
        fallback.assert_called_once()


if __name__ == '__main__':
    unittest.main()
