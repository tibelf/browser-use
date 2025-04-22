import logging
from functools import wraps
from typing import Callable, List, Tuple, Dict, Any, Union, Awaitable, Optional

from browser_use.agent.service import Agent
from browser_use.agent.views import AgentHistoryList, ActionModel, ActionResult
from browser_use.browser.context import BrowserContext
from browser_use.browser.views import BrowserState

from .service import ScreenshotPlugin

logger = logging.getLogger(__name__)

def create_screenshot_callbacks(plugin: ScreenshotPlugin) -> Tuple[
    Union[
        Callable[[BrowserState, Any, int], None],  # Sync callback
        Callable[[BrowserState, Any, int], Awaitable[None]],  # Async callback
    ],
    Union[
        Callable[[AgentHistoryList], Awaitable[None]],  # Async Callback
        Callable[[AgentHistoryList], None],  # Sync Callback
    ],
]:
    """
    Create callback functions for the agent to use with the screenshot plugin.
    
    Args:
        plugin: ScreenshotPlugin instance
        
    Returns:
        Tuple of (step_callback, done_callback) functions
    """
    
    async def step_callback(state: BrowserState, model_output: Any, step_number: int) -> None:
        """Callback for each step"""
        plugin.handle_step(state, model_output, step_number)
    
    async def done_callback(history: AgentHistoryList) -> None:
        """Callback when agent is done"""
        plugin.handle_done(history.model_dump().get("history", []))
    
    return step_callback, done_callback

def wrap_multi_act(original_multi_act: Callable, plugin: ScreenshotPlugin) -> Callable:
    """
    Wrap the agent's multi_act method to capture execution results and screenshots.
    
    Args:
        original_multi_act: Original multi_act method of the agent
        plugin: ScreenshotPlugin instance
        
    Returns:
        Wrapped multi_act function
    """
    @wraps(original_multi_act)
    async def wrapped_multi_act(
        actions: List[ActionModel],
        check_for_new_elements: bool = True,
    ) -> List[ActionResult]:
        # Call the original method
        results = await original_multi_act(actions, check_for_new_elements)
        
        # Get the current browser state after execution
        browser_context = getattr(wrapped_multi_act.__self__, 'browser_context', None)
        if browser_context and isinstance(browser_context, BrowserContext):
            try:
                state = await browser_context.get_state(cache_clickable_elements_hashes=True)
                # Handle execution with the plugin
                plugin.handle_execute(state, results)
            except Exception as e:
                logger.error(f"Error capturing screenshot after execution: {e}")
        
        return results
    
    # Set the self reference for the method (needed for bound methods)
    wrapped_multi_act.__self__ = original_multi_act.__self__
    
    return wrapped_multi_act

def setup_agent_with_screenshot_plugin(
    agent: Agent, 
    screenshot_dir: str = "screenshots",
    save_plans: bool = True
) -> ScreenshotPlugin:
    """
    Set up an agent with the screenshot plugin.
    
    This function configures the agent to use the screenshot plugin by:
    1. Creating the plugin instance
    2. Setting up callback functions
    3. Wrapping the multi_act method
    
    Args:
        agent: Agent instance to configure
        screenshot_dir: Directory to save screenshots
        save_plans: Whether to save plan information
        
    Returns:
        Configured ScreenshotPlugin instance
    """
    # Create the plugin instance
    plugin = ScreenshotPlugin(base_dir=screenshot_dir, save_plans=save_plans)
    
    # Set up callbacks
    step_callback, done_callback = create_screenshot_callbacks(plugin)
    agent.register_new_step_callback = step_callback
    agent.register_done_callback = done_callback
    
    # Wrap multi_act method
    original_multi_act = agent.multi_act
    agent.multi_act = wrap_multi_act(original_multi_act, plugin)
    
    # Add plugin to agent object
    agent.screenshot_plugin = plugin
    
    logger.info(f"Screenshot plugin configured for agent. Saving to: {screenshot_dir}")
    
    return plugin 
