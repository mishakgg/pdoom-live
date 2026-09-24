import os

import pytest

pytestmark = pytest.mark.live


@pytest.mark.skipif(os.environ.get("PDOOM_LIVE_TESTS") != "1", reason="set PDOOM_LIVE_TESTS=1 to call live APIs")
def test_openalex_author_search_responds():
    from pdoom_pipeline.fetch import SafeFetcher

    fetcher = SafeFetcher(allowed_content_types=("application/json",), max_attempts=2)
    result = fetcher.get(
        "https://api.openalex.org/authors?search=Dario%20Amodei&per-page=1&mailto=collector@pdoom.live"
    )
    assert result.status == 200
    assert b"results" in result.body
