#!/usr/bin/env python3
import logging
from ddgs import DDGS

logger = logging.getLogger('SEARCH_TOOL')


class SearchTool:
    def __init__(self):
        logger.info("Initializing Search Tool...")
        logger.info("[OK] Search Tool initialized")

    def search(self, query: str, max_results: int = 3) -> str:
        logger.info(f"[SEARCH] Searching: {query}")
        try:
            import time
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query,
                    max_results=max_results,
                    region='wt-wt',
                    safesearch='off',
                    timelimit=None,
                ))
            # Retry once with delay if empty (DDG rate limit)
            if not results:
                time.sleep(3)
                with DDGS() as ddgs:
                    results = list(ddgs.text(
                        query,
                        max_results=max_results,
                        region='wt-wt',
                        safesearch='off',
                    ))
            if not results:
                return f"No results found for: {query}"
            output = []
            for i, r in enumerate(results, 1):
                output.append(f"{i}. {r['title']}")
                output.append(f"   {r['body'][:150]}...")
                output.append(f"   URL: {r['href']}")
            return "\n".join(output)
        except Exception as e:
            logger.error(f"[SEARCH] Error: {str(e)}")
            return f"Search error: {str(e)}"
