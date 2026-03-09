import time
import json
import re
from test.linkedin import LinkedInTools
from test.resumeParser import parse_resume
from agent_pipeline.Agent.Agent import Agent
from agent_pipeline.Agent.Clients.GithubClient import GitHubModelsClient
from agent_pipeline.Agent.Clients.GeminiClient import GeminiClient # Or whichever you prefer
from Navigation.Tools.actions import ActionTools
from Navigation.Tools.perception import PerceptionTools
from Navigation.Tools.navigation import NavigationTools
from Navigation.Browser.manager import BrowserManager
from Navigation.Tools.Models.element import ElementStore
from agent_pipeline.utils.logger import Logger
from Navigation.DomMemoryManager import DOMAwareMemoryManager

session = BrowserManager(headless=False)
navigation_tools = NavigationTools(session)
element_store = ElementStore()
perception_tools = PerceptionTools(session, element_store)
job_tools = LinkedInTools(element_store)
logger = Logger()

resume_text = parse_resume("Resume.pdf")

WORKER_PROMPT = """
You are a specialized Job Application Worker. Your ONLY goal is to apply to the currently selected job.

**USER DATA:**
{user_context}

**PROTOCOL:**
1. Check if "Easy Apply" is visible. If not, report "Not Easy Apply" and STOP.
2. Click "Easy Apply".
3. Fill the form using User Data.
   - **Comboboxes (Location/Experience):** TYPE the value (e.g. "Kerala"), WAIT, then CLICK the option.
   - **Radio Buttons:** FORCE CLICK them if standard click fails.
   - **Uploads:** Use `upload_file` for Resume.
4. Click "Next" / "Review" / "Submit".
5. **CRITICAL:** Do NOT stop until you see "Application sent" or have successfully submitted.

**ERROR RECOVERY:**
- If a click fails, assume it's an overlay and try again.
- If you see "Please enter a valid answer", check for skipped required fields.
"""

ORCHESTRATOR_PROMPT = """
You are the Headhunter Orchestrator. You control the browser to find jobs and assign them to Workers.

**YOUR TOOLS:**
- `open_page(url)`: Go to LinkedIn.
- `click_elements(ids)`: Click filters (like "Easy Apply" button).
- `get_job_posting_ids(limit)`: Returns a list of job IDs on the current page.
- `apply_to_job_wrapper(job_id, job_title)`: **DELEGATE** the application to a Worker Agent.

**YOUR MISSION:**
1. Open "https://www.linkedin.com/jobs/search".
2. Take a snapshot to see the page.
3. **Filter Results:** Find and click the "Easy Apply" filter button.
4. **Get Jobs:** Use `get_job_posting_ids` to get the top 5 jobs.
5. **Loop:** For each job ID you found:
   - Call `apply_to_job_wrapper(job_id, job_title)`.
   - Read the result returned by the worker.
6. Stop when you have attempted 5 applications.
"""


def reset_ui(action_tools_instance):
    """
    Cleanup function to close any lingering modals before the next agent starts.
    This prevents the 'infinite loop' of agents getting stuck on the previous job's popup.
    """
    print("--- [SYSTEM] Cleaning UI State ---")
    try:
        perception_tools.take_snapshot()
        
        targets = [el.id for el in element_store.all() if "Dismiss" in (el.name or "") or "Close" in (el.name or "")]
        
        if targets:
            print(f"Closing lingering modal (IDs: {targets})")
            action_tools_instance.click_elements([targets[0]]) 
            time.sleep(1)
            
            perception_tools.take_snapshot()
            discard_targets = [el.id for el in element_store.all() if "Discard" in (el.name or "")]
            if discard_targets:
                action_tools_instance.click_elements([discard_targets[0]])
                time.sleep(1)
    except Exception as e:
        print(f"UI Reset warning: {e}")


def apply_to_job_wrapper(job_id: str, job_title: str, user_context: dict, action_tools_instance) -> str:
    """
    Spawns a Worker Agent to handle the specific application logic for one job.
    """
    print(f"\n >>> [ORCHESTRATOR] Delegating Job: {job_title} (ID: {job_id})")
    
    action_tools_instance.click_elements([job_id])
    time.sleep(3) 
    
    worker_agent = Agent(
        llm_client=GeminiClient(), 
        tools=[
            perception_tools.take_snapshot,
            action_tools_instance.click_elements,
            action_tools_instance.type_in_elements,
            action_tools_instance.upload_file
        ],

        system_prompt=WORKER_PROMPT.format(user_context=json.dumps(user_context)),
        max_steps=20, # Give it enough room for multi-page forms
        reasoning=True,
        show_thinking=True,
        memory_manager=DOMAwareMemoryManager(history_window=8, scratchpad_window=10)
    )
    print(user_context)
    
    try:
        result = worker_agent.run(f"Apply to the job: {job_title}")
        status = result.get('final_response', 'No response')
    except Exception as e:
        status = f"Worker Crashed: {str(e)}"
    
    print(f" <<< [WORKER FINISHED] Result: {status}")
    
    reset_ui(action_tools_instance)
    
    return status


def run_orchestrator(message: str, user_context: dict, resume_path: str):
    
    try:
        action_tools_instance = ActionTools(
            session, 
            element_store, 
            perception_tools, 
            file_path=resume_path
        )
        
        def apply_to_job_wrapper_with_context(job_id: str, job_title: str) -> str:
            return apply_to_job_wrapper(job_id, job_title, user_context, action_tools_instance)
        
        orchestrator_tools = [
            navigation_tools.open_page,
            perception_tools.take_snapshot,
            action_tools_instance.type_in_elements, 
            action_tools_instance.click_elements,
            job_tools.get_job_posting_ids,
            apply_to_job_wrapper_with_context 
        ]
        
        orchestrator = Agent(
            llm_client=GeminiClient(),
            tools=orchestrator_tools,
            system_prompt=ORCHESTRATOR_PROMPT,
            max_steps=15,
            reasoning=True,
            show_thinking=True
        )
        
        print(f"[Orchestrator] Starting with user: {user_context.get('name', 'Unknown')}")
        response = orchestrator.run(user_input=message)
        return response.get("final_response", "No response")
        
    except Exception as e:
        error_msg = f"Agent Error: {str(e)}"
        print(f"[Orchestrator] ERROR: {error_msg}")
        return error_msg