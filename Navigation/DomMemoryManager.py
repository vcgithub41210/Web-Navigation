import re
from typing import List
from agent_pipeline.Agent.Memory.standard import SlidingWindowMemory

class DOMAwareMemoryManager(SlidingWindowMemory):
    def __init__(self, history_window: int = 6, scratchpad_window: int = 6):
        super().__init__(history_window, scratchpad_window)
        
        self.active_dom_payload: str = ""
        self.MARKER = "<<DOM>>"
        self.last_dom_hash: str = ""

    def _hash_dom(self, dom_content: str) -> str:
        """Quick hash to detect if DOM actually changed"""
        return str(hash(dom_content[:500]))[:8]

    def add_scratchpad_entry(self, entry: str):
        print("\n\n")
        print(entry)
        print("\n\n")

        snapshot_pattern = r"(Observation \d+:.*?(?:Success|Error).*?)(elements:[\s\n]+)(.*)"
    
        navigation_pattern = r"(.*observation.*?IDs reset\..*?)(elements:\\n)(.*)"
        
        match = re.search(snapshot_pattern, entry, re.DOTALL | re.IGNORECASE) or \
                re.search(navigation_pattern, entry, re.DOTALL | re.IGNORECASE)

        if match:
            header_info = match.group(1)
            heavy_content = match.group(3).strip()
            
            new_hash = self._hash_dom(heavy_content)
            if new_hash == self.last_dom_hash:
                compressed_entry = header_info + "\n[DOM unchanged]"
                super().add_scratchpad_entry(compressed_entry)
                return
            
            for i in range(len(self.scratchpad)):
                if self.MARKER in self.scratchpad[i]:
                    self.scratchpad[i] = self.scratchpad[i].replace(
                        self.MARKER, 
                        f"[PREV DOM - {self.last_dom_hash}]" 
                    )
            
            self.last_dom_hash = new_hash
            self.active_dom_payload = heavy_content
            
            lightweight_entry = f"{header_info}\n{self.MARKER}"
            super().add_scratchpad_entry(lightweight_entry)
            
            print(f"[Memory] DOM updated ({len(heavy_content)} chars)")
            
        else:
            if len(entry) > 2000 and "elements" in entry.lower():
                print(f"[Memory] WARNING: Regex failed on massive output (len {len(entry)}). Truncating.")
                safe_entry = entry[:500] + f"\n... [SYSTEM TRUNCATED: MASSIVE OUTPUT FAILED PARSING]"
                super().add_scratchpad_entry(safe_entry)
            else:
                entry = self._compress_observation(entry)
                super().add_scratchpad_entry(entry)

    def _compress_observation(self, entry: str) -> str:
       
        entry = re.sub(r"'status': 'ok',?\s*", "", entry)
        entry = re.sub(r"'status': 'success',?\s*", "", entry)
        entry = entry.replace("Values updated in ", "↻")
        entry = entry.replace("Layout updated: ", "Δ")
        entry = re.sub(r"\{'element_id': '(\d+)', 'status': 'ok'\}", r"'\1✓'", entry)
        return entry

    def get_scratchpad(self) -> str:
        if not self.scratchpad:
            return "No actions taken yet."
        
        visible_entries = self.scratchpad[-self.scratchpad_window:]
        raw_text = "\n\n".join(visible_entries)
        
        if self.MARKER in raw_text:
            return raw_text.replace(self.MARKER, self.active_dom_payload)
        
        return raw_text
