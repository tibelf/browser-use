import json
import logging
import os
import base64
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
    
    def __init__(self, base_dir: str = "screenshots", save_plans: bool = True):
        """
        Initialize the screenshot plugin.
        
        Args:
            base_dir: Base directory for saving screenshots and plans
            save_plans: Whether to save plan information
        """
        self.base_dir = base_dir
        self.save_plans = save_plans
        self.current_step = 0
        self.plans = []
        
        # Create base directory if not exists
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)
        
    def save_screenshot(self, state: BrowserState, step_number: Optional[int] = None) -> str:
        """
        Save a screenshot of the current browser state.
        
        Args:
            state: Browser state containing the screenshot
            step_number: Custom step number, uses internal counter if None
            
        Returns:
            Path to the saved screenshot
        """
        if step_number is None:
            step_number = self.current_step
            
        # Create directory for this execution step
        execute_dir = self._create_execute_dir(step_number)
        
        # Save screenshot
        screenshot_path = os.path.join(execute_dir, "screenshot.png")
        
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
            "actions": [action.model_dump() for action in model_output.action],
            "next_goal": model_output.current_state.next_goal if model_output.current_state else None,
            "evaluation": model_output.current_state.evaluation_previous_goal if model_output.current_state else None,
        }
        
        # Save plan to the plans list
        self.plans.append(plan_data)
        
        # Save plan file
        plan_path = os.path.join(execute_dir, "plan.json")
        with open(plan_path, "w") as f:
            json.dump(plan_data, f, indent=2)
        
        logger.info(f"Plan saved to {plan_path}")
        return plan_path
    
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
                "extracted_content": r.extracted_content,
                "error": r.error,
                "success": r.success,
                "is_done": r.is_done,
                "include_in_memory": r.include_in_memory
            } 
            for r in results
        ]
        
        # Save results file
        results_path = os.path.join(execute_dir, "results.json")
        with open(results_path, "w") as f:
            json.dump(results_data, f, indent=2)
        
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
        self.save_screenshot(state, actual_step)
        self.save_plan(model_output, actual_step)
    
    def handle_execute(self, state: BrowserState, results: List[ActionResult]) -> None:
        """
        Handle execution result by saving screenshot and results.
        
        Args:
            state: Browser state
            results: Action results
        """
        # Save screenshot and results for current step
        self.save_screenshot(state)
        self.save_results(results)
        
        # Increment step counter after execution
        # Note: We increment after saving because the current step's data should be saved
        # with the current step number before moving to the next step
        self.current_step += 1
    
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_path = os.path.join(self.base_dir, f"execute_{step_number:03d}_{timestamp}")
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        return dir_path 
