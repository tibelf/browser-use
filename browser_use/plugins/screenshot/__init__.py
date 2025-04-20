from .service import ScreenshotPlugin
from .integration import setup_agent_with_screenshot_plugin, create_screenshot_callbacks, wrap_multi_act

__all__ = [
    'ScreenshotPlugin',
    'setup_agent_with_screenshot_plugin',
    'create_screenshot_callbacks',
    'wrap_multi_act',
] 