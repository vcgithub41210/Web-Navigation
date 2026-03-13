from typing import List, Dict
from Navigation.Tools.Models.element import ElementStore

class LinkedInTools:
    def __init__(self, element_store: ElementStore):
        self.element_store = element_store

    def get_job_posting_ids(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Returns a pool of available job postings from the current page.
        """
        all_elements = self.element_store.all()
        job_postings = []

        for el in all_elements:
            
            if el.role == "link" and el.name:

                excluded_names = ["LinkedIn", "Home", "My Network", "Jobs", "Messaging", "Notifications","Try Premium for ₹0"]
                if any(name in el.name for name in excluded_names):
                    continue
                
                job_postings.append({
                    "element_id": el.id,
                    "job_title": el.name
                })

        
        pool_size = max(limit, 10)
        return job_postings[:pool_size]
