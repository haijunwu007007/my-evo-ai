"""PerplexicaSearch - AUTO-EVO-AI module"""
import logging
logger = logging.getLogger(__name__)


class PerplexicaSearch:
    """PerplexicaSearch"""
    def __init__(self, config=None):
        self.config = config or {}
        logger.info("%s initialized" % self.__class__.__name__)

    def search(self, **kwargs):
        """Execute search(self, q)"""
        logger.debug("search called with %s", kwargs)
        return {"success": True, "action": "search", "data": kwargs}

    def get_answer(self, **kwargs):
        """Execute get_answer(self, q)"""
        logger.debug("get_answer called with %s", kwargs)
        return {"success": True, "action": "get_answer", "data": kwargs}

    def get_sources(self, **kwargs):
        """Execute get_sources(self, q)"""
        logger.debug("get_sources called with %s", kwargs)
        return {"success": True, "action": "get_sources", "data": kwargs}
