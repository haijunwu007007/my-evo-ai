
class HomeAssistant:
    def __init__(self): self.devices = {}; self._ready = True
    def status(self): return {"name": "home_assistant", "ready": self._ready, "devices": len(self.devices)}
    def list_devices(self): return [{"id": k, "name": v.get("name", k)} for k, v in self.devices.items()]
    def toggle(self, device_id, state): self.devices[device_id] = {"name": device_id, "state": state}
    def execute(self, action="", params=None):
        if action == "toggle": self.toggle((params or {}).get("device", ""), (params or {}).get("state", "on"))
        return self.status()
get_status = lambda: HomeAssistant().status()
