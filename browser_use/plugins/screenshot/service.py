import json
import logging
import os
import base64
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from browser_use.agent.views import AgentOutput, ActionResult
from browser_use.browser.views import BrowserState

logger = logging.getLogger(__name__)

class ScreenshotPlugin:
    """
    Plugin for saving screenshots and plan information during agent execution.
    
    This plugin saves browser screenshots for each execute step and plan information
    in a structured directory.
    """
    
    def __init__(self, base_dir: str = "screenshots", save_plans: bool = True, full_page: bool = True):
        """
        Initialize the screenshot plugin.
        
        Args:
            base_dir: Base directory for saving screenshots and plans
            save_plans: Whether to save plan information
            full_page: Whether to capture the full scrollable page
        """
        self.base_dir = base_dir
        self.save_plans = save_plans
        self.full_page = full_page
        self.current_step = 0
        self.plans = []
        self.current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create base directory if not exists
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)
        
    def save_screenshot(self, state: BrowserState, result_index: int = 0, step_number: Optional[int] = None) -> str:
        """
        Save a screenshot of the current browser state.
        
        Args:
            state: Browser state containing the screenshot
            result_index: Index of the result this screenshot corresponds to
            step_number: Custom step number, uses internal counter if None
            
        Returns:
            Path to the saved screenshot
        """
        if step_number is None:
            step_number = self.current_step
            
        # Create directory for this execution step
        execute_dir = self._create_execute_dir(step_number)
        
        # Save screenshot with result index
        screenshot_path = os.path.join(execute_dir, f"screenshot_{result_index}.png")
        
        if state.screenshot:
            try:
                # Convert base64 string back to binary data
                screenshot_bytes = base64.b64decode(state.screenshot)
                
                with open(screenshot_path, "wb") as f:
                    f.write(screenshot_bytes)
                logger.info(f"Screenshot saved to {screenshot_path}")
            except Exception as e:
                logger.error(f"Error saving screenshot: {e}")
        else:
            logger.warning("No screenshot available in browser state")
            
        return screenshot_path
    
    def save_plan(self, model_output: AgentOutput, step_number: Optional[int] = None) -> str:
        """
        Save plan information from the model output.
        
        Args:
            model_output: Agent output containing plan information
            step_number: Custom step number, uses internal counter if None
            
        Returns:
            Path to the saved plan file
        """
        if not self.save_plans:
            return ""
            
        if step_number is None:
            step_number = self.current_step
            
        # Create directory for this execution step
        execute_dir = self._create_execute_dir(step_number)
        
        # Extract plan information
        plan_data = {
            "step_number": step_number,
            "timestamp": datetime.now().isoformat(),
            "current_state": model_output.current_state.model_dump() if model_output.current_state else None,
            "actions": [action.model_dump() for action in model_output.action]
            #"next_goal": model_output.current_state.next_goal if model_output.current_state else None,
            #"evaluation": model_output.current_state.evaluation_previous_goal if model_output.current_state else None,
        }
        
        # Save plan to the plans list
        self.plans.append(plan_data)
        
        # Save plan file
        plan_path = os.path.join(execute_dir, "plan.json")
        with open(plan_path, "w") as f:
            json.dump(plan_data, f, indent=2)
        
        logger.info(f"Plan saved to {plan_path}")
        return plan_path
    
    @staticmethod
    def JSON_to_dict(text):
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                # 返回解析后的JSON对象
                return json.loads(json_str)
            except json.JSONDecodeError:
                # 如果解析失败，返回处理后的文本字符串
                return text
        else:
            # 如果没有找到JSON块，返回处理后的文本字符串
            return text
        

    def save_results(self, results: List[ActionResult], step_number: Optional[int] = None) -> str:
        """
        Save action results.
        
        Args:
            results: List of action results
            step_number: Custom step number, uses internal counter if None
            
        Returns:
            Path to the saved results file
        """
        if step_number is None:
            step_number = self.current_step
            
        # Create directory for this execution step
        execute_dir = self._create_execute_dir(step_number)
        
        # Extract results data
        results_data = [
            {
                "extracted_content": self.JSON_to_dict(r.extracted_content) if r.extracted_content else None,
                "error": r.error,
                "success": r.success,
                "is_done": r.is_done,
                "include_in_memory": r.include_in_memory
            } 
            for r in results
        ]
        
        # Save results file
        results_path = os.path.join(execute_dir, "results.json")
        with open(results_path, "w", encoding='utf-8') as f:
            json_str = json.dumps(results_data, indent=2, ensure_ascii=False)
            f.write(json_str)
        
        logger.info(f"Results saved to {results_path}")
        return results_path
    
    def handle_step(self, state: BrowserState, model_output: AgentOutput, step_number: int) -> None:
        """
        Handle a new agent step by saving screenshot and plan.
        
        Args:
            state: Browser state
            model_output: Agent output
            step_number: Step number (already incremented by Agent)
        """
        # Since step_number is already incremented in Agent.step(),
        # we need to subtract 1 to get the correct step number for saving
        actual_step = step_number - 1
        self.current_step = actual_step
        
        # Save initial screenshot for the step
        self.save_screenshot(state, 0, actual_step)
        self.save_plan(model_output, actual_step)
    
    def handle_done(self, history: List[Dict]) -> None:
        """
        Handle agent completion by saving all plans.
        
        Args:
            history: Agent history
        """
        self.save_all_plans()
    
    def save_all_plans(self) -> None:
        """Save all collected plans to a single file"""
        if not self.save_plans or not self.plans:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        all_plans_path = os.path.join(self.base_dir, f"all_plans_{timestamp}.json")
        
        with open(all_plans_path, "w") as f:
            json.dump(self.plans, f, indent=2)
            
        logger.info(f"All plans saved to {all_plans_path}")
    
    def _create_execute_dir(self, step_number: int) -> str:
        """
        Create directory for an execution step.
        
        Args:
            step_number: Step number
            
        Returns:
            Path to the execution directory
        """
        dir_path = os.path.join(self.base_dir, f"execute_{step_number:03d}_{self.current_timestamp}")
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        return dir_path 

    async def take_screenshot(self, browser_context) -> str:
        """Take a screenshot of the current page."""
        try:
            screenshot_path = await browser_context.take_screenshot(full_page=self.full_page)
            return screenshot_path
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
