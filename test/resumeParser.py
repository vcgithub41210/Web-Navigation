import pymupdf
import re

def resume_to_string(resume: str)-> str:
    out = pymupdf.open(resume)
    text = []
    for page in out:
        text.append(page.get_text()) 
    out.close()
    return "".join(text)

def clean_raw_text(raw_text):
    if isinstance(raw_text, bytes):
        raw_text = raw_text.decode('utf-8')
    
   
    cleaned = raw_text.encode("ascii", "ignore").decode()

    cleaned = re.sub(r'[\t\r\n]+', ' ', cleaned)

    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned

def parse_resume(resume: str) -> str:
    text = resume_to_string(resume)
    cleaned_text = clean_raw_text(text)
    return cleaned_text
