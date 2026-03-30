import time
import json
import re
from test.linkedin import LinkedInTools
from agent_pipeline.Agent.Agent import Agent
from agent_pipeline.Agent.Clients.GithubClient import GitHubModelsClient
from agent_pipeline.Agent.Clients.GeminiClient import GeminiClient 
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
- `get_job_posting_ids()`: Returns a pool of job postings from the current page. Always call with NO arguments to get the full pool.
- `apply_to_job_wrapper(job_id, job_title)`: **DELEGATE** the application to a Worker Agent.
- `take_snapshot()`: View the current state of the page.

**YOUR MISSION:**
1. Open "https://www.linkedin.com/jobs/search". 
2. Take a snapshot to see the page. 
3. **Filter Results:** Find and click the "Easy Apply" filter button.
4. **Get Jobs:** Call `get_job_posting_ids()` with NO limit argument — this returns your full candidate pool.
5. **Loop:** Go through the pool one by one:
   - Call `apply_to_job_wrapper(job_id, job_title)` for the next candidate.
   - If the worker reports "Not Easy Apply" or fails, skip it and move to the next candidate in the pool.
   - Stop once you have **successfully attempted 5 applications** (skipped jobs do not count).
6. If the entire pool is exhausted before reaching 5, stop and report what was attempted.

**CRITICAL ANTI-LOOP RULES:**
- **NEVER** call `open_page` more than once per session. 
- If you take a snapshot and the page appears blank, incomplete, or is taking time to load, **DO NOT RELOAD**. Wait a moment by doing nothing, then take another snapshot to check again.
"""


def _extract_company(job_title: str, status: str) -> str:
    """
    Best-effort company extraction.
    1. Try "at <Company>" in the job title.
    2. Try common patterns in the worker's status message.
    3. Fallback to "Unknown Company".
    """

    m = re.search(r'\bat\s+([A-Z][^\s,\.]+(?:\s+[A-Z][^\s,\.]*)*)', job_title)
    if m:
        return m.group(1).strip()

    for pattern in [
        r'(?:applied to|sent to|submitted to|application to|at)\s+([A-Z][A-Za-z0-9& ]{1,40}?)(?:\s*[-–,\.]|$)',
        r'([A-Z][A-Za-z0-9&]{2,}(?:\s+[A-Z][A-Za-z0-9&]{2,})?)\s+(?:job|role|position)',
    ]:
        m = re.search(pattern, status)
        if m:
            return m.group(1).strip()

    return "Unknown Company"


def _build_autoapply_summary(job_log: list, stopped: bool = False, raw: str = "", error: str = "") -> str:
    """
    Formats the final response shown to the user in the chat.
    """
    count = len(job_log)
    if count == 0:
        if error:
            return f"AutoApply stopped due to an error: {error}"
        if stopped:
            return "AutoApply was interrupted before any applications could be processed."
        return raw or "No jobs were processed."

    successes = [j for j in job_log if j.get("success")]
    header = (
        f"AutoApply stopped after {count} application{'s' if count != 1 else ''}."
        if stopped
        else f"AutoApply complete! Attempted {count} job{'s' if count != 1 else ''}."
    )

    lines = [header, ""]
    for j in job_log:
        icon = "✅" if j.get("success") else "❌"
        company = j.get("company", "")
        suffix = f" @ {company}" if company and company != "Unknown Company" else ""
        lines.append(f"{icon} **{j['title']}**{suffix} — {j['result']}")

    lines.append(f"\nSuccessfully applied: {len(successes)}/{count}")
    return "\n".join(lines)

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


def apply_to_job_wrapper(
    job_id: str,
    job_title: str,
    user_context: dict,
    action_tools_instance,
    on_job_applied=None,
    job_log=None,
) -> str:
    """
    Spawns a Worker Agent to handle the specific application logic for one job.
    Records the result in job_log (list). Calls on_job_applied on success.
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
        max_steps=20,
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

    success_keywords = ["application sent", "applied", "submitted", "success"]
    is_success = any(kw in status.lower() for kw in success_keywords)
    company = _extract_company(job_title, status)

    if job_log is not None:
        short_result = status[:120].strip() if len(status) > 120 else status.strip()
        job_log.append({
            "title": job_title,
            "company": company,
            "success": is_success,
            "result": short_result,
        })

    if is_success and on_job_applied:
        try:
            on_job_applied({
                "position": job_title,
                "company": company,
                "link": f"https://www.linkedin.com/jobs/view/{job_id}",
            })
        except Exception as cb_err:
            print(f"[WORKER] Job-applied callback error: {cb_err}")

    reset_ui(action_tools_instance)
    
    return status


def run_chat_response(message: str, user_context: dict) -> str:
    """
    Lightweight conversational response using the user's profile as background.
    Does not open a browser or trigger any automation.
    """
    name = user_context.get("name", "the user")
    role = user_context.get("desired_role", "not specified")
    skills = ", ".join(user_context.get("skills", []) or [])
    experience = user_context.get("experience", "not specified")
    about = user_context.get("about", "")

    system_prompt = (
        f"You are JobAgent, a helpful AI assistant specializing in job searching and career advice.\n"
        f"You are assisting a user with the following profile:\n"
        f"- Name: {name}\n"
        f"- Desired role: {role}\n"
        f"- Key skills: {skills}\n"
        f"- Experience: {experience}\n"
        f"- About: {about}\n\n"
        f"Answer the user's question helpfully and concisely. "
        f"If they want to apply to jobs automatically, let them know they can type something like "
        f"'Apply to software engineer jobs' and the Auto Apply agent will handle it."
    )

    llm = GeminiClient()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]
    try:
        return llm.generate_response(messages)
    except Exception as e:
        return f"I'm having trouble responding right now. Please try again. ({e})"


def run_orchestrator(message: str, user_context: dict, resume_path: str, on_job_applied=None, job_log=None):

    if job_log is None:
        job_log = []

    try:
        action_tools_instance = ActionTools(
            session, 
            element_store, 
            perception_tools, 
            file_path=resume_path
        )
        
        def apply_to_job_wrapper_with_context(job_id: str, job_title: str) -> str:
            return apply_to_job_wrapper(
                job_id, job_title, user_context, action_tools_instance, on_job_applied, job_log
            )
        
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
        raw = response.get("final_response", "")
        return _build_autoapply_summary(list(job_log), stopped=False, raw=raw)

    except (KeyboardInterrupt, SystemExit):
        print("[Orchestrator] Interrupted — building partial summary.")
        return _build_autoapply_summary(list(job_log), stopped=True)

    except Exception as e:
        error_msg = str(e)
        print(f"[Orchestrator] ERROR: {error_msg}")
        return _build_autoapply_summary(list(job_log), stopped=True, error=error_msg)
