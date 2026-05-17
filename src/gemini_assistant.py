import google.generativeai as genai
import json
import time
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiAssistant:
    """
    Gemini API Integration for PESCE Campus AI Chatbot.
    Handles context building, prompt engineering, query processing, and error handling.
    """
    def __init__(self, api_key: str, pesce_data: dict, model_name: str = 'gemini-2.0-flash'):
        self.api_key_valid = False
        if api_key and api_key != "your_gemini_api_key_here" and api_key != "your_claude_api_key_here":
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(model_name)
                self.api_key_valid = True
                logger.info(f"Gemini API configured successfully with model {model_name}.")
            except Exception as e:
                logger.error(f"Failed to configure Gemini API: {e}")
                self.model = None
        else:
            self.model = None
            logger.warning("Gemini API key not provided. Assistant will run in fallback/offline mode.")
            
        self.pesce_data = pesce_data
        
    def build_context(self, query: str) -> str:
        """
        Extract relevant data from pesce_data based on query keywords.
        Builds a targeted context to keep the prompt size manageable and focused.
        """
        if not self.pesce_data:
            return "No college data available."
            
        query_lower = query.lower()
        relevant_sections = []
        
        # Simple keyword-based routing to specific JSON sections
        if any(w in query_lower for w in ["admission", "apply", "fee", "document", "eligibility"]):
            relevant_sections.append(("Admissions", self.pesce_data.get("admissions", {})))
            
        if any(w in query_lower for w in ["placement", "company", "recruit", "package", "salary", "offer"]):
            relevant_sections.append(("Placements", self.pesce_data.get("placements", {})))
            
        if any(w in query_lower for w in ["hostel", "library", "canteen", "medical", "sport", "facility"]):
            relevant_sections.append(("Facilities", self.pesce_data.get("facilities", {})))
            
        if any(w in query_lower for w in ["contact", "phone", "email", "address", "reach"]):
            relevant_sections.append(("Contact", self.pesce_data.get("contact", {})))
            
        if any(w in query_lower for w in ["course", "program", "department", "branch", "b.e", "m.tech", "phd"]):
            relevant_sections.append(("UG Departments", self.pesce_data.get("departments_ug", {})))
            relevant_sections.append(("PG Departments", self.pesce_data.get("departments_pg", {})))
            
        if any(w in query_lower for w in ["about", "vision", "mission", "principal", "history"]):
            relevant_sections.append(("About PESCE", self.pesce_data.get("about", {})))
            
        # If no specific section matches strongly, include general info + homepage stats
        if not relevant_sections:
            relevant_sections.append(("Homepage & Stats", self.pesce_data.get("homepage", {})))
            
        # Build context string
        context_parts = []
        for section_name, data in relevant_sections:
            context_parts.append(f"--- {section_name.upper()} ---")
            # Flatten the dictionary for text context
            context_parts.append(self._flatten_dict(data))
            
        # Limit context length to avoid overwhelming the token limit
        full_context = "\n".join(context_parts)
        return full_context[:8000] # Return up to ~8000 characters of context
        
    def _flatten_dict(self, d: dict, prefix="") -> str:
        """Helper to flatten dictionary into readable text."""
        parts = []
        if isinstance(d, dict):
            for k, v in d.items():
                if k in ["images", "_metadata"]: continue # Skip heavy/irrelevant keys
                if isinstance(v, (dict, list)):
                    parts.append(self._flatten_dict(v, f"{prefix}{k} > "))
                else:
                    parts.append(f"{prefix}{k}: {v}")
        elif isinstance(d, list):
            for item in d[:10]: # Limit list items
                if isinstance(item, (dict, list)):
                    parts.append(self._flatten_dict(item, prefix))
                else:
                    parts.append(f"{prefix}- {item}")
        elif isinstance(d, str):
            if len(d) > 20: # Only include meaningful strings
                parts.append(f"{prefix}{d[:500]}") # Truncate very long strings
        return "\n".join(parts)

    def generate_response(self, user_query: str, chat_history: list = None, personality: str = "Friendly", language: str = "English", retries: int = 2) -> tuple[str, list]:
        """
        Generates a response using Gemini, incorporating context and handling errors.
        Returns a tuple: (response_text, list_of_followup_suggestions)
        """
        if not self.api_key_valid or not self.model:
            return self._fallback_response(user_query), []
            
        context = self.build_context(user_query)
        chat_history = chat_history or []
        
        tones = {
            "Formal": "Respond formally and professionally. Avoid slang.",
            "Friendly": "Be warm, friendly, encouraging, and use emojis naturally.",
            "Expert": "Provide detailed, precise, and highly informative technical answers.",
            "Student": "Use casual, relatable, student-friendly language. Be helpful like a peer.",
            "Parent": "Be reassuring, highly informative, thorough, and address safety/academic concerns."
        }
        
        system_prompt = f"""You are a helpful AI assistant for P.E.S. College of Engineering (PESCE), Mandya.
Your goal is to answer questions about the college using ONLY the provided data.
Tone: {tones.get(personality, tones['Friendly'])}
Language: Respond entirely in {language}.

GUIDELINES:
1. Be accurate, friendly, and helpful.
2. If information is not available in the context, clearly state: "I don't have that specific information right now." Do not hallucinate facts.
3. Be concise but informative. Format your response nicely with markdown (bullet points, bold text).
4. Cite sources implicitly (e.g., "According to the placement records...").
5. Include emojis for visual appeal where appropriate.
6. AT THE VERY END of your response, suggest exactly 2 or 3 relevant follow-up questions the user might want to ask. Format each follow-up on a new line starting with the exact string "FOLLOWUP: ".

CONTEXT FROM PESCE DATA:
{context}
"""
        
        # Build conversation history text
        history_text = ""
        for msg in chat_history[-4:]: # Only include last 4 messages to save tokens
            role = "User" if msg["role"] == "user" else "AI"
            history_text += f"{role}: {msg['content']}\n"
            
        prompt = f"{system_prompt}\n\nCONVERSATION HISTORY:\n{history_text}\n\nUSER QUESTION: {user_query}\nAI RESPONSE:"
        
        # Retry logic for rate limits / API errors
        for attempt in range(retries):
            try:
                response = self.model.generate_content(prompt)
                
                if not response.text:
                    raise ValueError("Empty response received from Gemini.")
                    
                full_text = response.text
                
                # Parse out the follow-ups
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
                error_msg = str(e).lower()
                if "quota" in error_msg or "rate limit" in error_msg or "429" in error_msg:
                    logger.warning(f"Rate limit hit. Retrying in {2 ** attempt} seconds...")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    logger.error(f"Gemini API Error: {e}")
                    return f"⚠️ **API Error:** {str(e)[:100]}.\n\n*Falling back to offline mode...*\n\n{self._fallback_response(user_query)}", []
                    
        return f"⚠️ **Service Unavailable:** We are currently experiencing high traffic. Please try again in a few moments.\n\n*Offline response:* {self._fallback_response(user_query)}", []

    def _fallback_response(self, query: str) -> str:
        """Simple keyword matching when API is down or key is missing."""
        q = query.lower()
        if "admission" in q: return "Admissions are merit-based via CET, COMED-K. Contact: admissions@pesce.ac.in"
        if "placement" in q: return "PESCE has 359+ visiting companies with top recruiters like TCS, Infosys, and Wipro."
        if "hostel" in q: return "Separate boys (350 capacity) and girls (371 capacity) hostels are available with WiFi and mess."
        if "fee" in q: return "Fee structures vary by entry type (CET/COMED-K/Mgmt). Please contact admissions."
        if "contact" in q: return "Call +91 8232 220043 or email principal@pesce.ac.in"
        return "I can help with Admissions, Placements, Hostels, Courses, and Contact info. What would you like to know?"

# ==========================================
# Testing Block
# ==========================================
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    API_KEY = os.getenv("GOOGLE_API_KEY")
    
    print("Loading local data...")
    try:
        with open("../data/processed/pesce_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        try:
            with open("data/processed/pesce_data.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {"admissions": {"process": "CET based"}}
            print("Data file not found. Using dummy data for testing.")
            
    print("\nInitializing Gemini Assistant...")
    assistant = GeminiAssistant(api_key=API_KEY, pesce_data=data)
    
    test_queries = [
        "What is the admission process?",
        "Tell me about CSE placements.",
        "Are there hostel facilities?"
    ]
    
    for q in test_queries:
        print(f"\n{'='*50}\nQ: {q}\n{'-'*50}")
        # Test context building
        ctx = assistant.build_context(q)
        print(f"Context length generated: {len(ctx)} chars")
        
        # Test full response generation
        print("\nGenerating AI Response...")
        start = time.time()
        resp, followups = assistant.generate_response(q, personality="Friendly")
        print(f"Time taken: {time.time() - start:.2f}s")
        print(f"\nResponse:\n{resp}")
        print(f"\nFollow-ups suggested:\n- " + "\n- ".join(followups))
