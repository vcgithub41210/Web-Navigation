import json
from agent_pipeline.Agent.Agent import Agent
from agent_pipeline.Agent.Clients.GeminiClient import GeminiClient
from Navigation.Tools.actions import ActionTools
from Navigation.Tools.perception import PerceptionTools
from Navigation.Tools.navigation import NavigationTools
from Navigation.Browser.manager import BrowserManager
from Navigation.Tools.Models.element import ElementStore
from agent_pipeline.utils.logger import Logger
from Navigation.DomMemoryManager import DOMAwareMemoryManager

# Initialize global singletons for the browser session
session = BrowserManager(headless=False)
navigation_tools = NavigationTools(session)
element_store = ElementStore()
shared_memory = DOMAwareMemoryManager(history_window=4, scratchpad_window=6)  
perception_tools = PerceptionTools(session, element_store)
logger = Logger()

# We use a function to generate the prompt dynamically per user
def get_system_prompt(user_context: dict) -> str:
    # Convert the user_context dictionary into a formatted JSON string
    context_str = json.dumps(user_context, indent=2)
    
    return f"""
You are an autonomous Form Filling Agent. Your goal is to complete the Google Form submission successfully.

**USER CONTEXT (IMMUTABLE TRUTH):**
{context_str}

**AUTONOMOUS MODE (CRITICAL):**
1. **NO CHATCHAT:** Do NOT return text responses like "I have filled the page" or "Ready for next step".
2. **CHAINING:** You must keep calling tools (type/click/upload) continuously until the form is submitted.
3. **ONLY STOP WHEN:** You see the exact text "Your response has been recorded" or "Thank you for your submission".

**PROTOCOL:**
1. **Analyze:** Check the snapshot.
   - If "Required question" fields are empty -> **FILL THEM**.
   - If "Next" button is visible -> **CLICK IT**.
   - If "Submit" button is visible -> **CLICK IT**.
2. **Handle Data:**
   - Map the USER CONTEXT provided above to form fields (e.g., name, education, skills).
   - If the context lacks data, generate a plausible placeholder (e.g., "N/A" or "0").
3. **Uploads:**
   - Found "Add file" button? -> Call `upload_file(element_id)`.
   - Wait for the upload to finish (snapshot will show a file icon) before clicking Next/Submit.

**UI HANDLING RULES:**
- **Radio Buttons:** If clicking the circle fails, click the *Text Label* associated with it.
- **Dropdowns:** Click Trigger -> WAIT -> Click Option.
- **Date Fields:** Type "01-01-2000" if exact DOB is unknown.

**DEFINITION OF DONE:**
Your final response MUST ONLY be: "Form submitted successfully." 
Do not output this until you see the confirmation screen.
"""

# The run_agent function now matches the signature of your LinkedIn orchestrator
def run_agent(message: str, user_context: dict, resume_path: str):
    try:
        # 1. Initialize ActionTools with the dynamic resume path downloaded from Supabase
        action_tools = ActionTools(
            session, 
            element_store, 
            perception_tools, 
            file_path=resume_path
        )

        # 2. Inject the dynamic context into the prompt
        current_system_prompt = get_system_prompt(user_context)

        # 3. Create the agent
        agent = Agent(
            llm_client = GeminiClient(),
            system_prompt=current_system_prompt,
            tools=[
                perception_tools.take_snapshot,
                navigation_tools.open_page,
                action_tools.click_elements,
                action_tools.type_in_elements,
                action_tools.set_date,
                action_tools.upload_file
            ],
            max_steps=50,  
            max_retries=3,  
            reasoning=False,
            show_thinking=True,
            memory_manager=shared_memory
        )

        print(f"[GoogleForm Agent] Starting form fill with context for: {user_context.get('name', 'User')}")
        response = agent.run(user_input=message)
        return response.get("final_response", "No response")
        
    except Exception as e:
        error_msg = f"Agent Error: {str(e)}"
        print(f"[GoogleForm Agent] ERROR: {error_msg}")
        return error_msg
