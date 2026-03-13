from Navigation.Browser.manager import BrowserManager
from Navigation.Tools.Models.element import ElementStore
from Navigation.normalization.normalize_actions import _normalize_actions, _normalize_ids
from Navigation.Tools.ToolHelpers.action_helper import _observe_and_report
from Navigation.Tools.perception import PerceptionTools 
import time
import random
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

class ActionTools:
    def __init__(self, session, element_store, perception_tools,file_path):
        self.session = session
        self.element_store = element_store
        self.perception = perception_tools
        self.file_path = file_path 

    def click_elements(self, element_ids: list[str]):
        """
        Clicks on a list of web elements identified by their unique IDs.
        """
        results = []
        try:
            page = self.session.get_page()
            
            for eid in element_ids:
                try:
                    el = self.element_store.get(eid)
                    if not el: raise ValueError(f"ID {eid} not found")

                    loc = page.locator(el.selector).first

                    
                    if el.role == "option":
                        is_native = loc.evaluate("el => el.tagName === 'OPTION'")
                        if is_native:
                            parent = loc.locator("xpath=..")
                            val = loc.get_attribute("value")
                            if val: parent.select_option(val)
                            else: parent.select_option(label=loc.text_content())
                            results.append({"element_id": eid, "status": "ok", "note": "native_select"})
                            continue

                    try:
                        loc.scroll_into_view_if_needed()
                        loc.click(timeout=2000) 
                        results.append({"element_id": eid, "status": "ok"})
                    
                    except Exception as e:
                        print(f"Standard click failed for {eid}: {e}. Retrying with FORCE...")
                        try:
                            loc.click(force=True, timeout=2000)
                            results.append({"element_id": eid, "status": "ok", "note": "force_clicked"})
                        
                        except Exception as e2:
                            print(f"Force click failed for {eid}: {e2}. Dispatching JS click...")
                            loc.dispatch_event("click")
                            results.append({"element_id": eid, "status": "ok", "note": "js_dispatched"})

                except Exception as e:
                    print(f"All attempts failed for {eid}: {e}")
                    results.append({"element_id": eid, "status": "error", "reason": str(e)})
            
            base = {"status": "partial" if any(r["status"]=="error" for r in results) else "ok", "results": results}
            time.sleep(1)
            return _observe_and_report(base, self.perception)

        except Exception as e:
            return {"status": "error", "reason": str(e)}



    def type_in_elements(self, entries: list[dict]):
        """
        Types text into a list of web elements.

        Args:
            entries (list[dict]): A list of data entries to type. 
                                  Each entry MUST be a dictionary with:
                                  - "element_id" (str): The ID of the field.
                                  - "text" (str): The text to type.
        """
        results = []
        try:
            page = self.session.get_page()
            
            for entry in entries: 
                eid = entry.get("element_id")
                text = entry.get("text")
                
                try:
                    el = self.element_store.get(eid)
                    if not el: raise ValueError(f"ID {eid} not found")
                    loc = page.locator(el.selector).first
                    loc.fill("")
                    loc.type(text)
                    results.append({"element_id": eid, "status": "ok"})
                except Exception as e: 
                    results.append({"element_id": eid, "status": "error", "reason": str(e)})

            base = {"status": "partial" if any(r["status"]=="error" for r in results) else "ok", "results": results}
            
            return _observe_and_report(base, self.perception)
        except Exception as e: 
            return {"status": "error", "reason": str(e)}


    def set_date(self, element_id: str, date_str: str):
        """
        Sets the date in a date input field. Date should be in YYYY-MM-DD format
        """
        try:
            element = self.element_store.get(element_id)
            page = self.session.get_page()
            locator = page.locator(element.selector)
            
            if element.attributes.get('type') == 'date':
                locator.fill(date_str)
                return {"status": "success", "method": "native_date_input"}
            
            
            try:
                locator.click()
                locator.fill(date_str)
                page.keyboard.press("Enter")
                return {"status": "success", "method": "text_fill"}
            except:
                pass

            page.evaluate(
                "(element, value) => { element.value = value; element.dispatchEvent(new Event('input', {bubbles: true})); element.dispatchEvent(new Event('change', {bubbles: true})); }", 
                locator.element_handle(), 
                date_str
            )
            return {"status": "success", "method": "js_injection"}

        except Exception as e:
            return {"status": "error", "reason": str(e)}
    


    
    def upload_file(self, element_id: str):
        """
        Uploads a file to a file input id
        """
        try:
            page = self.session.get_page()
            el = self.element_store.get(element_id)
            if not el: raise ValueError(f"ID {element_id} not found")
            
            locator = page.locator(el.selector).first
            locator.wait_for(state="visible", timeout=3000)

            
            try:
                with page.expect_file_chooser(timeout=2000) as fc_info:
                    locator.click()
                
                file_chooser = fc_info.value
                file_chooser.set_files(self.file_path)
                return _observe_and_report({"status": "ok", "results": [{"element_id": element_id, "status": "uploaded"}]}, self.perception)

            except PlaywrightTimeoutError:
                print("Direct upload timed out. Searching for Google Picker modal...")
                
                time.sleep(2)

                browse_btn = None
                
                if page.get_by_text("Browse", exact=True).is_visible():
                    browse_btn = page.get_by_text("Browse", exact=True)
                elif page.get_by_text("Select files from your device").is_visible():
                    browse_btn = page.get_by_text("Select files from your device")
                
                if not browse_btn:
                    for frame in page.frames:
                        try:
                            if frame.get_by_text("Browse", exact=True).is_visible():
                                browse_btn = frame.get_by_text("Browse", exact=True)
                                print("Found 'Browse' button inside an iframe.")
                                break
                            if frame.get_by_text("Select files from your device").is_visible():
                                browse_btn = frame.get_by_text("Select files from your device")
                                print("Found 'Select files' button inside an iframe.")
                                break
                        except:
                            continue 

                if browse_btn:
                    with page.expect_file_chooser(timeout=10000) as fc_info:
                        browse_btn.click()
                    
                    file_chooser = fc_info.value
                    file_chooser.set_files(self.file_path)
                    
                    time.sleep(3) 
                    
                    return _observe_and_report({"status": "ok", "results": [{"element_id": element_id, "status": "uploaded_via_modal"}]}, self.perception)
                else:
                    raise Exception("Could not find 'Browse' or 'Select files' button in any frame.")

        except Exception as e:
            return {"status": "error", "reason": str(e)}
