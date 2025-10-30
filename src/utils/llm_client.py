"""LLM Client for Azure OpenAI integration"""
import os
import json
from openai import AzureOpenAI
from typing import Dict, Any
from .config import Config

class LLMClient:
    def __init__(self):
        if not Config.LLM_ENDPOINT or not Config.AZURE_OPENAI_KEY:
            raise ValueError("LLM configuration missing. Check .env file.")
        
        self.client = AzureOpenAI(
            api_key=Config.AZURE_OPENAI_KEY,
            api_version=Config.OPENAI_API_VERSION,
            azure_endpoint=Config.LLM_ENDPOINT
        )
        self.model = Config.DEFAULT_MODEL
    
    def analyze_incident(self, incident: Dict, candidates: list) -> Dict[str, Any]:
        """
        Use LLM to analyze incident and rank candidates with reasoning.
        
        Args:
            incident: Incident data
            candidates: List of candidate persons with scores
            
        Returns:
            Dict with recommendations and explanations
        """
        
        prompt = self._build_analysis_prompt(incident, candidates)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"LLM Error: {e}")
            return self._get_fallback_response(candidates)
    
    def _build_analysis_prompt(self, incident: Dict, candidates: list) -> str:
        """Build the prompt for LLM analysis"""
        
        candidates_text = ""
        for i, candidate in enumerate(candidates, 1):
            candidates_text += f"""
Candidate {i}: {candidate.get('name', 'N/A')} (ID: {candidate.get('user_id', 'N/A')})
  - Skills: {candidate.get('skills', 'N/A')}
  - Group: {candidate.get('group', 'N/A')}
  - On-Call: {candidate.get('on_call', 'No')}
  - Max Capacity: {candidate.get('max_concurrent', 'N/A')}
  - Initial Score: {candidate.get('score', 0)}
"""
        
        prompt = f"""
INCIDENT DETAILS:
- Short Description: {incident.get('short_description', 'N/A')}
- Description: {incident.get('description', 'N/A')}
- Category: {incident.get('category', 'N/A')}
- Subcategory: {incident.get('subcategory', 'N/A')}
- Priority: {incident.get('priority', 'P3')}
- Opened At: {incident.get('opened_at', 'N/A')}

CANDIDATES:
{candidates_text}

REQUIRED OUTPUT (JSON):
{{
  "top1": {{
    "name": "Candidate Name",
    "user_id": "ID",
    "recommendation_score": 85,
    "primary_reason": "skill_match",
      "reasons": [
        "Skill match: Database",
        "On-call status provides immediate response",
        "Workload capacity available"
      ],
    "explanation": "Best match because..."
  }},
  "top2": {{ "name": "...", "user_id": "...", "recommendation_score": ..., "primary_reason": "...", "reasons": [...], "explanation": "..." }},
  "top3": {{ "name": "...", "user_id": "...", "recommendation_score": ..., "primary_reason": "...", "reasons": [...], "explanation": "..." }},
  "overall_analysis": "Brief analysis of the incident urgency and candidate fit"
}}

PRIMARY REASONS to use:
- "skill_match": Subcategory matches person's skills
- "on_call": Person is currently on-call
- "workload": High max capacity available
- "priority": Match on incident priority handling
- "shift": Within shift hours

Be concise but specific.
"""
        return prompt
    
    def _get_system_prompt(self) -> str:
        """System prompt for LLM"""
        return """You are an expert ticket assignment assistant. 
Analyze incidents and recommend the best team members for assignment.
Provide structured JSON responses with scores (0-100) and clear explanations.
Focus on skill matching, on-call status, workload capacity, and incident priority."""
    
    def _get_fallback_response(self, candidates: list) -> Dict:
        """Fallback response if LLM fails"""
        if len(candidates) == 0:
            return {}
        
        result = {}
        for i, candidate in enumerate(candidates[:3], 1):
            result[f'top{i}'] = {
                "name": candidate.get('name', 'N/A'),
                "user_id": candidate.get('user_id', 'N/A'),
                "recommendation_score": candidate.get('score', 50),
                "primary_reason": "fallback",
                "reasons": ["Automatic fallback response"],
                "explanation": "LLM unavailable, using score-based ranking"
            }
        
        result['overall_analysis'] = "Automated fallback response"
        return result

