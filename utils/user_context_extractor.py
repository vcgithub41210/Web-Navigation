import json
from test.resumeParser import parse_resume
from agent_pipeline.Agent.Clients.GeminiClient import GeminiClient

_DEFAULT_EXPECTED_CTC = "500000"  # 5 LPA default


def _apply_ctc_defaults(ctx: dict) -> dict:
    """If expected_ctc is missing, zero, or empty, default to 5 LPA."""
    raw = str(ctx.get("expected_ctc", "")).strip()
    if not raw or raw in ("0", "0.0", "null", "None"):
        ctx["expected_ctc"] = _DEFAULT_EXPECTED_CTC
    return ctx


def extract_user_context(resume_path: str) -> dict:
    
    try:
        resume_text = parse_resume(resume_path)
        
        if not resume_text or len(resume_text) < 50:
            raise Exception("Resume text is empty or too short")
        
        llm_client = GeminiClient()
        
        extraction_prompt = f"""
You are an expert resume parser.

Extract structured information from the resume text and return a STRICT JSON object.

Rules:
- Return ONLY valid JSON.
- Do NOT include explanations or markdown.
- Do NOT hallucinate information.
- If a field is missing, use the default value.

JSON SCHEMA

{{
  "name": "string",
  "phone": "string",
  "phone_country_code": "string",
  "email": "string",
  "work_experience": [
      {{
        "job_title": "string",
        "company": "string",
        "duration": "string",
        "skills_used": ["string"]
      }}
  ],
  "current_location": "string",
  "willing_to_relocate": "Yes/No",
  "total_experience_years": "string",
  "current_ctc": "string",
  "expected_ctc": "string",
  "notice_period_months": "string",
  "skills": ["string"]
}}

Extraction rules:

name → candidate full name. Default "Unknown".

phone → digits only, no country code. Default "".

phone_country_code → format "Country (+code)". Default "India (+91)".

email → primary email. Default "".

work_experience → list of roles with job_title, company, duration, skills_used.  
If none → [].

current_location → city/state/country if present. Default "India".

willing_to_relocate → "Yes" if unclear.

total_experience_years → numeric string calculated from experience.  
Student/fresher → "0".

current_ctc → numeric string. Default "0".

expected_ctc → candidate's expected salary as a numeric string (annual, INR).
If not mentioned, use "500000" (5 LPA default).

notice_period_months → numeric months (Immediate → "0").

skills → list of unique normalized technical skills.

RESUME TEXT:
{resume_text}

Return ONLY the JSON object.
"""
        
        messages = [{"role": "user", "content": extraction_prompt}]
        response = llm_client.generate_response(messages)
        
        try:
            response_text = response.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            user_context = json.loads(response_text.strip())
            
            required_fields = ["name", "phone", "email", "current_location", "skills"]
            for field in required_fields:
                if field not in user_context:
                    print(f"[WARNING] Missing field '{field}' in extracted context")
                    user_context[field] = ""

            user_context = _apply_ctc_defaults(user_context)
            
            print("[Extractor] Successfully extracted user context:")
            print(json.dumps(user_context, indent=2))
            
            return user_context
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse LLM response as JSON: {str(e)}")
            print(f"LLM Response: {response}")
            raise Exception("Failed to extract structured data from resume")
            
    except Exception as e:
        print(f"[ERROR] User context extraction failed: {str(e)}")
        
        return {
            "name": "Unknown",
            "phone": "",
            "phone_country_code": "India (+91)",
            "email": "",
            "current_location": "",
            "willing_to_relocate": "Yes",
            "total_experience_years": "0",
            "current_ctc": "0",
            "expected_ctc": _DEFAULT_EXPECTED_CTC,
            "notice_period_months": "0",
            "skills": []
        }

    
    try:
        resume_text = parse_resume(resume_path)
        
        if not resume_text or len(resume_text) < 50:
            raise Exception("Resume text is empty or too short")
        
        llm_client = GeminiClient()
        
        extraction_prompt = f"""
You are an expert resume parser.

Extract structured information from the resume text and return a STRICT JSON object.

Rules:
- Return ONLY valid JSON.
- Do NOT include explanations or markdown.
- Do NOT hallucinate information.
- If a field is missing, use the default value.

JSON SCHEMA

{{
  "name": "string",
  "phone": "string",
  "phone_country_code": "string",
  "email": "string",
  "work_experience": [
      {{
        "job_title": "string",
        "company": "string",
        "duration": "string",
        "skills_used": ["string"]
      }}
  ],
  "current_location": "string",
  "willing_to_relocate": "Yes/No",
  "total_experience_years": "string",
  "current_ctc": "string",
  "expected_ctc": "string",
  "notice_period_months": "string",
  "skills": ["string"]
}}

Extraction rules:

name → candidate full name. Default "Unknown".

phone → digits only, no country code. Default "".

phone_country_code → format "Country (+code)". Default "India (+91)".

email → primary email. Default "".

work_experience → list of roles with job_title, company, duration, skills_used.  
If none → [].

current_location → city/state/country if present. Default "India".

willing_to_relocate → "Yes" if unclear.

total_experience_years → numeric string calculated from experience.  
Student/fresher → "0".

current_ctc → numeric string. Default "0".

expected_ctc → if missing use current_ctc.

notice_period_months → numeric months (Immediate → "0").

skills → list of unique normalized technical skills.

RESUME TEXT:
{resume_text}

Return ONLY the JSON object.
"""
        
        messages = [{"role": "user", "content": extraction_prompt}]
        response = llm_client.generate_response(messages)
        
        try:
            response_text = response.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            user_context = json.loads(response_text.strip())
            
            required_fields = ["name", "phone", "email", "current_location", "skills"]
            for field in required_fields:
                if field not in user_context:
                    print(f"[WARNING] Missing field '{field}' in extracted context")
                    user_context[field] = ""
            
            print("[Extractor] Successfully extracted user context:")
            print(json.dumps(user_context, indent=2))
            
            return user_context
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse LLM response as JSON: {str(e)}")
            print(f"LLM Response: {response}")
            raise Exception("Failed to extract structured data from resume")
            
    except Exception as e:
        print(f"[ERROR] User context extraction failed: {str(e)}")
        
        return {
            "name": "Unknown",
            "phone": "",
            "phone_country_code": "India (+91)",
            "email": "",
            "current_location": "",
            "willing_to_relocate": "Yes",
            "total_experience_years": "0",
            "current_ctc": "0",
            "expected_ctc": "0",
            "notice_period_months": "0",
            "skills": []
        }
