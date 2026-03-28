import inspect
import asyncio
from typing import List, Optional
from agent_pipeline.Tool_Execution.parse_tool_call import generate_available_tools, parse_tool_calls
from agent_pipeline.utils.parser import extract_tagged_content
from agent_pipeline.utils.logger import Logger
from agent_pipeline.Agent.Abstactions.AbstractMemory import MemoryManager
from agent_pipeline.Agent.Memory.standard import SlidingWindowMemory

logger = Logger()

BASE_INSTRUCTIONS = """
You are a precise agent.

**Previous Conversation:**
__CHAT_HISTORY__

**Current User Goal:**
__QUESTION__

**Available Tools:**
<tools>
__TOOLS__
</tools>

**Scratchpad (Current Task Progress):**
__SCRATCHPAD__

**CRITICAL RULES:**
1. Analyze the goal, history, and tools.
2. Review the Scratchpad to see what has already been done.
3. **CHECK FOR COMPLETION:** If the Scratchpad shows that the required tool actions have already been completed successfully, **DO NOT** run them again. Instead, take the result from the Observation and output it as your <final_answer>.
4. **DO NOT** output any conversational text. Use ONLY the tags below.
5. **DECISION PROTOCOL:**
   - If you need to use a tool -> Use **Format 1 (Tool Call)**.
   - If you have completed the instruction or need to stop -> Use **Format 2 (Final Answer)**.
   - **NEVER** use both in the same response.

__FORMAT_INSTRUCTIONS__
"""

REASONING_INSTRUCTIONS = """
**Format 1: If you need to use a tool**
<thinking>
Brief reasoning on why you need this tool.
</thinking>
<tool_call>
{"name": "function-name", "arguments": { ... }}
</tool_call>
*Note: Do NOT wrap the JSON in markdown code blocks (```).*

**Format 2: Final Answer (Mission Complete or Question Answered)**
<thinking>
Reasoning on how you arrived at the answer.
</thinking>
<final_answer>The specific answer or instruction.</final_answer>
"""

DIRECT_INSTRUCTIONS = """
**Format 1: Tool Call (Single or Batch)**
For efficiency, you can execute multiple actions in a single list:
<tool_call>
[
    {"name": "func1", "arguments": { ... }},
    {"name": "func2", "arguments": { ... }}
]
</tool_call>

**Format 2: Final Answer**
<final_answer>The answer.</final_answer>
"""

class Agent:
    def __init__(self, llm_client, tools, memory_manager: Optional[MemoryManager] = None, max_steps=5, max_retries=2, reasoning=True, show_thinking=True, system_prompt=None):
        self.llm_client = llm_client
        self.tools = tools
        self.function_map = {func.__name__: func for func in tools}
        self.max_steps = max_steps
        self.max_retries = max_retries
        self.reasoning = reasoning
        self.show_thinking = show_thinking
        self.system_prompt = system_prompt
        
        if memory_manager:
            self.memory = memory_manager
        else:
            self.memory = SlidingWindowMemory(history_window=6, scratchpad_window=10)
    
    def optimize_prompt_whitespace(self, text: str) -> str:
        
        lines = [line.strip() for line in text.split('\n')]
        non_empty_lines = [line for line in lines if line]
        
        clean_text = "\n".join(non_empty_lines)
        
        return clean_text

    def _call_llm(self, prompt: str) -> str:

        optimized_prompt = self.optimize_prompt_whitespace(prompt)
        optimized_system = self.optimize_prompt_whitespace(self.system_prompt) if self.system_prompt else None
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": optimized_system})
        messages.append({"role": "user", "content": optimized_prompt})
        return self.llm_client.generate_response(messages)
    
    def run(self, user_input: str): 
        
        if self.tools:
            available_tools_str = generate_available_tools(self.tools)
        else:
            available_tools_str = "No tools available."

        if self.reasoning:
            current_format = REASONING_INSTRUCTIONS
        else:
            current_format = DIRECT_INSTRUCTIONS

        for i in range(self.max_steps):
            
            history_str = self.memory.get_context()
            current_scratchpad = self.memory.get_scratchpad()
            
            prompt = BASE_INSTRUCTIONS.replace("__CHAT_HISTORY__", history_str) \
                                      .replace("__QUESTION__", user_input) \
                                      .replace("__TOOLS__", available_tools_str) \
                                      .replace("__SCRATCHPAD__", current_scratchpad) \
                                      .replace("__FORMAT_INSTRUCTIONS__", current_format)

            llm_response = self._call_llm(prompt)
            if not llm_response or not llm_response.strip():
                self.memory.add_scratchpad_entry(f"Observation {i+1}: Error. You returned an empty response. Please output a valid <tool_call> or <final_answer>.")
                continue

            if self.show_thinking:
                thinking_process = extract_tagged_content(llm_response, "thinking")
                if thinking_process:
                    logger.thought(thinking_process)

            final_answer = extract_tagged_content(llm_response, "final_answer")
            if final_answer:
                self.memory.add_message("User", user_input)
                self.memory.add_message("Assistant", final_answer)
                return {
                    "final_response": final_answer, 
                    "history": self.memory.get_raw_scratchpad()
                }

            # --- FIXED EXECUTION LOOP ---
            try:
                # 1. Get the LIST of tools
                tool_calls = parse_tool_calls(llm_response)
                
                if tool_calls:
                    logs = []
                    stop_sequence = False

                    # 2. Iterate through the list
                    for idx, tool in enumerate(tool_calls):
                        t_name = tool.get("name")
                        t_args = tool.get("arguments", {})

                        if t_name not in self.function_map:
                            logs.append(f"Action {idx+1}: Error - Tool '{t_name}' not found. SEQUENCE ABORTED.")
                            stop_sequence = True
                            break
                        
                        # Execute
                        print(f"Executing {t_name} args={t_args}")
                        func = self.function_map[t_name]
                        
                        try:
                            if inspect.iscoroutinefunction(func):
                                result = asyncio.run(func(**t_args))
                            else:
                                result = func(**t_args)
                            
                            # Soft Error Check
                            if isinstance(result, dict) and result.get('status') == 'error':
                                logs.append(f"Action {idx+1} ({t_name}): Failed - {result.get('reason')}. SEQUENCE ABORTED.")
                                stop_sequence = True
                                break

                            logs.append(f"Action {idx+1} ({t_name}): Success - {result}")

                        except Exception as e:
                            logs.append(f"Action {idx+1} ({t_name}): Execution Exception - {e}. SEQUENCE ABORTED.")
                            stop_sequence = True
                            break
                    
                    # 3. Consolidate Log
                    final_log = "\n".join(logs)
                    if stop_sequence and len(logs) < len(tool_calls):
                        skipped = len(tool_calls) - len(logs)
                        final_log += f"\n(Note: {skipped} subsequent actions were skipped due to previous failure.)"
                        
                    self.memory.add_scratchpad_entry(f"Observation {i+1}:\n{final_log}")
                
                else:
                    self.memory.add_scratchpad_entry(f"Observation {i+1}: Error. No valid <tool_call> tags found.")
                    continue

            except Exception as e:
                self.memory.add_scratchpad_entry(f"Observation {i+1}: Execution Error: {e}")

        failure_msg = "I could not complete the task within the given steps."
        self.memory.add_message("User", user_input)
        self.memory.add_message("Assistant", failure_msg)

        return {
            "final_response": failure_msg,
            "history": self.memory.get_raw_scratchpad()
        }