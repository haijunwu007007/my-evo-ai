"""JoyAIVLInteraction - AUTO-EVO-AI module"""
import logging
logger = logging.getLogger(__name__)


class JoyAIVLInteraction:
    """JoyAIVLInteraction"""
    def __init__(self, config=None):
        self.config = config or {}
        logger.info("%s initialized" % self.__class__.__name__)

    def describe(self, **kwargs):
        """Execute describe(self, image)"""
        logger.debug("describe called with %s", kwargs)
        return {"success": True, "action": "describe", "data": kwargs}

    def ask(self, **kwargs):
        """Execute ask(self, image, question)"""
        logger.debug("ask called with %s", kwargs)
        return {"success": True, "action": "ask", "data": kwargs}

    def detect(self, **kwargs):
        """Execute detect(self, image, object)"""
        logger.debug("detect called with %s", kwargs)
        return {"success": True, "action": "detect", "data": kwargs}
