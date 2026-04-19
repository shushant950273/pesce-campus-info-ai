import streamlit as st
from sentence_transformers import SentenceTransformer, util
import time

@st.cache_resource
def load_semantic_model():
    """
    Loads `all-MiniLM-L6-v2` once into memory.
    - Extremely lightweight (~80MB RAM required).
    - Very fast (computes locally without GPU).
    - Perfect for matching context/meaning over strict keywords.
    """
    return SentenceTransformer('all-MiniLM-L6-v2')

class SemanticSearcher:
    def __init__(self, data):
        self.data = data
        self.model = load_semantic_model()
        self.corpus = []
        self.corpus_keys = []
        
        # 1. Translate JSON into massive "Semantic Facts" paragraph representations
        self._build_corpus()
        
        # 2. Pre-compute Document Embeddings via cache for zero-latency lookups
        self.embeddings = self._get_cached_embeddings()

    def _build_corpus(self):
        """Translates basic JSON parameters into rich semantic paragraphs for the transformer to map meaning."""
        for category, content in self.data.items():
            if category == "academics":
                ug_progs = ", ".join([p.get("name", "") for p in content.get("undergraduate_programs", [])])
                fact = f"Academics, education, learning, and studies. We offer a {content.get('structure')} program. Engineering branches, departments, and streams taught include: {ug_progs}. We heavily teach Artificial Intelligence, Machine Learning (AI & ML), CSE, engineering sciences. Semester division is {content.get('semester_schedule', {}).get('odd', '')}. Exam grading pattern is {content.get('exam_pattern')}."
                self.corpus.append(fact)
                self.corpus_keys.append("academics")

            elif category == "placements":
                comps = ", ".join(content.get("top_companies", []))
                fact = f"Placements, recruitment, jobs, careers, hiring, earnings, making money, and salaries. {content.get('companies_visited')} companies visited for campus recruitment. {content.get('students_placed')} students successfully placed and hired. Total job offers secured: {content.get('total_offers')}. Top recruiting companies include {comps}."
                self.corpus.append(fact)
                self.corpus_keys.append("placements")
                
            elif category == "facilities":
                fact = f"Campus facility, infrastructure, living, sleeping, eating, health, and campus life. Library size: {content.get('library', {}).get('area', '')}. Boys hostel and girls hostel dormitory accommodation for staying and sleeping. Boys capacity: {content.get('boys_hostel', {}).get('total_capacity')}. Girls capacity: {content.get('girls_hostel', {}).get('total_inmates')}. Medical dispensary and doctor available. Food canteen. Sports grounds including {', '.join(content.get('sports', {}).get('facilities', []))}."
                self.corpus.append(fact)
                self.corpus_keys.append("facilities")
                
            elif category == "administrative":
                types = ", ".join([a.get('type', '') for a in content.get("admission_types", [])])
                docs = ", ".join(content.get("required_documents", []))
                fact = f"Administrative, rules, contact, phone numbers, email, principal, management, cost, and payment. Admission types accepted are {types}. Principal name is {content.get('principal')}. Admission contact email is {content.get('admission_email')} and phone is {content.get('admission_phone')}. Required documents for entry: {docs}."
                self.corpus.append(fact)
                self.corpus_keys.append("administrative")
            
            elif category == "faq":
                fact = "Frequently asked questions, doubts, queries, help, what, where, when, how. Covers admissions, academics, placements, hostels, and general campus facilities."
                self.corpus.append(fact)
                self.corpus_keys.append("faq")
                
    def _get_cached_embeddings(self):
        # We process this string array into mathematically mapped numerical tensors!
        return self.model.encode(self.corpus, convert_to_tensor=True)
        
    def search(self, query, threshold=0.45):
        """
        Embeds the incoming user query into vector space, and searches its 
        closest nearest-neighbor against our cached `embeddings` database!
        """
        if not self.data: return None, None, 0.0
        
        # Small contextual injection to help the lightweight model with colloquial slang
        enhancement = ""
        q_lower = query.lower()
        if any(w in q_lower for w in ["sleep", "bed", "live", "staying"]): enhancement = " hostel dormitory facilities"
        elif any(w in q_lower for w in ["money", "salary", "pay", "earn"]): enhancement = " jobs placements recruiting"
             
        query_embedding = self.model.encode(query + enhancement, convert_to_tensor=True)
        
        # util.semantic_search calculates Cosine Similarity efficiently
        hits = util.semantic_search(query_embedding, self.embeddings, top_k=1)[0]
        
        best_hit = hits[0] # {"corpus_id": 1, "score": 0.65}
        best_score = best_hit['score']
        
        if best_score > threshold:
            matched_category = self.corpus_keys[best_hit['corpus_id']]
            content = dict(self.data[matched_category])
            
            # Post-match tagging / highlighting based on semantic wins
            if matched_category == "academics" and ("ai" in q_lower or "machine learning" in q_lower):
                 content["semantic_insight"] = "💡 You asked about AI: Yes, PESCE explicitly offers a program in Artificial Intelligence and Machine Learning!"
                 
            return content, matched_category, best_score
            
        return None, None, best_score
