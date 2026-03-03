import json
from test.linkedin import LinkedInTools
from agent_pipeline.Agent.Agent import Agent
from agent_pipeline.Agent.Clients.GroqClient import GroqClient
from agent_pipeline.Agent.Clients.OpenRouterClient import OpenRouterClient
from agent_pipeline.Agent.Clients.GeminiClient import GeminiClient
from agent_pipeline.Agent.Clients.GithubClient import GitHubModelsClient
from Navigation.Tools.actions import ActionTools
from Navigation.Tools.perception import PerceptionTools
from Navigation.Tools.navigation import NavigationTools
from Navigation.Browser.manager import BrowserManager
from Navigation.Tools.Models.element import ElementStore
from agent_pipeline.utils.logger import Logger
from Navigation.DomMemoryManager import DOMAwareMemoryManager

from test.resumeParser import parse_resume

session = BrowserManager(headless=False)
navigation_tools = NavigationTools(session)
element_store = ElementStore()
shared_memory = DOMAwareMemoryManager(history_window=4, scratchpad_window=6)  
perception_tools = PerceptionTools(session, element_store)
action_tools = ActionTools(session, element_store, perception_tools,file_path="Resume.pdf")
logger = Logger()

resume_text = ""
def get_resume_contents()-> str:
    """
    returns the content of the user's resume as a string.
    Can be used to infer for some details that are necessary to fill forms.
    Example: Name, Education, Skills, Date of Birth, Email, Phone Number, etc.
    """
    return resume_text

resume_text = parse_resume("Resume.pdf")

SYSTEM_PROMPT_TEMPLATE = """
You are an autonomous Form Filling Agent. Your goal is to complete the Google Form submission successfully.

**USER CONTEXT (IMMUTABLE TRUTH):**
    "current_location": "Kerala, India",
    "resume_path": "Resume.pdf"

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
   - Use `get_resume_contents` ONCE if you need education/experience details.
   - Map resume text (e.g., "BMC, thrikkakara") to form fields (e.g., "University").
   - If resume lacks data, generate a plausible placeholder (e.g., "N/A" or "0").
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


agent = Agent(
    llm_client = GeminiClient(),
    system_prompt=SYSTEM_PROMPT_TEMPLATE,
    tools=[
        perception_tools.take_snapshot,
        navigation_tools.open_page,
        action_tools.click_elements,
        action_tools.type_in_elements,
        action_tools.set_date,
        action_tools.upload_file,
        get_resume_contents
    ],
    max_steps=50,  
    max_retries=3,  
    reasoning=False,
    show_thinking=True,
    memory_manager=shared_memory
)

"""
Open this google form https://docs.google.com/forms/d/e/1FAIpQLSe_nn_5k-5-GMe5h6J9lF_-G8wuluhGSGWh10frU_nOn7tDOQ/viewform?usp=dialog and fill it. im yadunandan, email:yadunandanv08@gmail.com, DOB: 08/11/2002,
phone: 6238922215, final year student btech cs, i know python and java, aws, azure, gcp, good with git, and an ml engineer, i expect 1000000 salary. I found this job on linkedin.
"""
"""
Open this google form https://docs.google.com/forms/d/e/1FAIpQLSeIIOkuFqPagjWMam4HcxOLzgdtYfdWELNhtVombwUrEpXSew/viewform?usp=publish-editor and you will notice a field to upload resume. please upload the resume and submit the form.
"""
#User Prompt

"""
I want you to open the following google form: https://docs.google.com/forms/d/e/1FAIpQLSdilm5f2e31TXguYONDLVpSNXBBcZTMViiigjKrV76uCA9mzA/viewform?usp=dialog and fill the form. Please upload the resume and ensure all required fiels are filled. Make sure all the pages are checked and finally submit the form.
"""
while True:
    user_input = input("YOU: ")
    if user_input.lower() == 'exit':
        break
    
    response = agent.run(user_input=user_input)
    logger.info(f"Response: {response}")
    print("AGENT:", response['final_response'])
