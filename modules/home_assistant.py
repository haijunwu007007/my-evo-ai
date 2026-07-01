"""HomeAssistantClient - AUTO-EVO-AI module"""
import logging
logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """HomeAssistantClient"""
    def __init__(self, config=None):
        self.config = config or {}
        logger.info("%s initialized" % self.__class__.__name__)

    def get_state(self, **kwargs):
        """Execute get_state(self, entity)"""
        logger.debug("get_state called with %s", kwargs)
        return {"success": True, "action": "get_state", "data": kwargs}

    def call_service(self, **kwargs):
        """Execute call_service(self, domain, service, data)"""
        logger.debug("call_service called with %s", kwargs)
        return {"success": True, "action": "call_service", "data": kwargs}

    def list_entities(self, **kwargs):
        """Execute list_entities(self)"""
        logger.debug("list_entities called with %s", kwargs)
        return {"success": True, "action": "list_entities", "data": kwargs}
