import json
import time
import logging
import os
try:
    from groq import Groq
except ImportError:
    Groq = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiAssistant:
    """
    AI Assistant Integration for PESCE Campus AI Chatbot.
    Now upgraded to use Groq (Llama-3) for blazing fast, reliable responses without rate limits!
    """
    def __init__(self, api_key: str, pesce_data: dict, model_name: str = 'llama-3.3-70b-versatile'):
        self.api_key_valid = False
        
        # We will use the Groq API key instead for better reliability
        groq_key = os.getenv("GROQ_API_KEY")
        
        if groq_key and Groq:
            try:
                self.client = Groq(api_key=groq_key)
                self.model_name = model_name
                self.api_key_valid = True
                logger.info(f"Groq API configured successfully with model {model_name}.")
            except Exception as e:
                logger.error(f"Failed to configure Groq API: {e}")
                self.client = None
        else:
            self.client = None
            logger.warning("Groq API key not provided. Assistant will run in fallback/offline mode.")
            
        self.pesce_data = pesce_data
        
    def build_context(self, query: str) -> str:
        """Extract relevant data from pesce_data based on query keywords."""
        if not self.pesce_data:
            return "No college data available."
            
        query_lower = query.lower()
        relevant_sections = []
        
        if any(w in query_lower for w in ["admission", "apply", "fee", "document", "eligibility"]):
            relevant_sections.append(("Admissions", self.pesce_data.get("admissions", {})))
            
        if any(w in query_lower for w in ["placement", "company", "recruit", "package", "salary", "offer"]):
            relevant_sections.append(("Placements", self.pesce_data.get("placements", {})))
            
        if any(w in query_lower for w in ["hostel", "library", "canteen", "medical", "sport", "facility"]):
            relevant_sections.append(("Facilities", self.pesce_data.get("facilities", {})))
            
        if any(w in query_lower for w in ["contact", "phone", "email", "address", "reach"]):
            relevant_sections.append(("Contact", self.pesce_data.get("contact", {})))
            
        if any(w in query_lower for w in ["course", "program", "department", "branch", "b.e", "m.tech", "phd", "hod", "faculty"]):
            relevant_sections.append(("UG Departments", self.pesce_data.get("departments_ug", {})))
            
        if any(w in query_lower for w in ["about", "vision", "mission", "principal", "history"]):
            relevant_sections.append(("About PESCE", self.pesce_data.get("about", {})))
            
        # ALWAYS append a Master Summary of Courses, FAQs, and Locations so the bot NEVER fails basic questions
        master_summary = {
            "Undergraduate (B.E.) Courses": [
                "Computer Science & Engineering (CSE)",
                "Electronics & Communication Engineering (ECE)",
                "Mechanical Engineering",
                "Civil Engineering",
                "Electrical & Electronics Engineering (EEE)",
                "Information Science & Engineering (ISE)",
                "Artificial Intelligence & Machine Learning (AI&ML)",
                "Data Science (DS)",
                "Computer Science & Business Systems (CSBS)",
                "Automobile Engineering",
                "Industrial & Production Engineering",
                "Robotics & Artificial Intelligence",
                "VLSI Design & Technology"
            ],
            "Postgraduate Courses": [
                "Master of Computer Applications (MCA)",
                "Master of Business Administration (MBA)",
                "M.Tech in CSE, Machine Design, VLSI & ES, Civil CAD"
            ],
            "Frequently Asked Questions (FAQs)": {
                "Is it autonomous or private?": "PESCE is a government-aided autonomous engineering college established in 1962 under VTU, Belagavi and approved by AICTE.",
                "What are the accepted entrance exams?": "Admissions are primarily based on KCET for Karnataka students and COMEDK UGET for out-of-state students. Management quota is also available.",
                "What is the eligibility criteria?": "10+2 with Physics & Math as mandatory subjects, securing at least 45% aggregate marks (40% for reserved categories).",
                "Are there scholarships?": "Yes, various government/state-level scholarships are available, including the Supernumerary Quota (SNQ) for reduced fees.",
                "What is the fee structure?": "Fees vary based on admission quota (CET, COMEDK, Management). Please check the official college website or contact admissions@pesce.ac.in for current exact fees.",
                "Where is it located?": "Mandya, Karnataka. It has a beautiful 55+ acres lush green campus."
            },
            "Campus Navigation & Locations (Google Maps Data)": {
                "College Canteen": "The canteen is on the same lane of the college entry gate, around 300 meters away from the main gate in the same lane.",
                "Central Library": "Located at the heart of the campus, near the main administrative block.",
                "CSE Department": "Located in the newer academic block behind the main building.",
                "Boys Hostel": "Located inside the campus, near the sports ground.",
                "Girls Hostel": "Located securely within the campus premises with strict security.",
                "Main Gate": "Faces the main Mandya city road, providing easy access to transport."
            }
        }
        relevant_sections.append(("Master Summary (Courses, FAQs & Campus Map)", master_summary))
            
        if not relevant_sections:
            relevant_sections.append(("Homepage & Stats", self.pesce_data.get("homepage", {})))
            
        context_parts = []
        for section_name, data in relevant_sections:
            context_parts.append(f"--- {section_name.upper()} ---")
            context_parts.append(self._flatten_dict(data))
            
        full_context = "\n".join(context_parts)
        return full_context[:6000] # Safe context window for Llama
        
    def _flatten_dict(self, d: dict, prefix="") -> str:
        parts = []
        if isinstance(d, dict):
            for k, v in d.items():
                if k in ["images", "_metadata"]: continue
                if isinstance(v, (dict, list)):
                    parts.append(self._flatten_dict(v, f"{prefix}{k} > "))
                else:
                    parts.append(f"{prefix}{k}: {v}")
        elif isinstance(d, list):
            for item in d[:15]: 
                if isinstance(item, (dict, list)):
                    parts.append(self._flatten_dict(item, prefix))
                else:
                    parts.append(f"{prefix}- {item}")
        elif isinstance(d, str):
            if len(d) > 10:
                parts.append(f"{prefix}{d[:500]}")
        return "\n".join(parts)

    def generate_response(self, user_query: str, chat_history: list = None, personality: str = "Friendly", language: str = "English", retries: int = 1) -> tuple[str, list]:
        """Generates a response using Groq API."""
        if not self.api_key_valid or not self.client:
            return self._fallback_response(user_query), []
            
        context = self.build_context(user_query)
        
        tones = {
            "Professional": "Respond formally and professionally. Avoid slang.",
            "Friendly": "Be warm, friendly, encouraging, and use emojis naturally.",
            "Expert": "Provide detailed, precise, and highly informative technical answers.",
            "Student": "Use casual, relatable, student-friendly language. Be helpful like a peer.",
            "Parent": "Be reassuring, highly informative, thorough, and address safety/academic concerns."
        }
        
        system_prompt = f"""You are the official AI assistant for P.E.S. College of Engineering (PESCE), Mandya.
Your goal is to answer questions about the college using ONLY the provided context data.
Tone: {tones.get(personality, tones['Friendly'])}
Language: Respond entirely in {language}.

GUIDELINES:
1. Be accurate and helpful. Do NOT hallucinate.
2. If the info is NOT in the context, say "I don't have that specific information right now."
3. Be concise. Format beautifully with markdown (bullet points, bold text).
4. Include emojis where appropriate.
5. AT THE VERY END, suggest exactly 2 relevant follow-up questions. Format each on a new line starting with "FOLLOWUP: ".

CONTEXT DATA:
{context}
"""
        messages = [{"role": "system", "content": system_prompt}]
        
        if chat_history:
            for msg in chat_history[-3:]:
                messages.append({"role": msg["role"], "content": str(msg.get("content", ""))})
                
        messages.append({"role": "user", "content": user_query})
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model_name,
                temperature=0.3,
                max_tokens=1024,
            )
            
            full_text = chat_completion.choices[0].message.content
            
            lines = full_text.split('\n')
            main_response = []
            followups = []
            
            for line in lines:
                if line.strip().startswith("FOLLOWUP:"):
                    followups.append(line.replace("FOLLOWUP:", "").strip())
                else:
                    main_response.append(line)
                    
            return "\n".join(main_response).strip(), followups
            
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            return f"⚠️ **API Error:** {str(e)[:100]}.\n\n*Falling back to offline mode...*\n\n{self._fallback_response(user_query)}", []

    def _fallback_response(self, query: str) -> str:
        q = query.lower()
        if "admission" in q: return "Admissions are merit-based via CET, COMED-K. Contact: admissions@pesce.ac.in"
        if "placement" in q: return "PESCE has 359+ visiting companies with top recruiters like TCS, Infosys, and Wipro."
        if "hostel" in q: return "Separate boys (350 capacity) and girls (371 capacity) hostels are available with WiFi and mess."
        return "I can help with Admissions, Placements, Hostels, Courses, and Contact info. What would you like to know?"
