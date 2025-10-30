"""LLM-powered reasoning module"""
import pandas as pd
from typing import Dict, List
from ..utils.llm_client import LLMClient
from ..utils.config import Config

class Reasoner:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    def generate_recommendations(self, incident: Dict, top_candidates: pd.DataFrame) -> Dict:
        """
        Use LLM to generate recommendations with explanations.
        
        Args:
            incident: Incident data
            top_candidates: Top-K candidates
            
        Returns:
            Dict with LLM recommendations
        """
        # Convert DataFrame to list of dicts
        candidates_list = self._format_candidates(top_candidates)
        
        # Get LLM analysis
        llm_result = self.llm_client.analyze_incident(incident, candidates_list)
        
        # Merge with original candidate data
        recommendations = self._merge_recommendations(llm_result, top_candidates)
        
        return recommendations
    
    def _format_candidates(self, candidates: pd.DataFrame) -> List[Dict]:
        """Format candidates for LLM input"""
        result = []
        for idx, row in candidates.iterrows():
            # Handle potential NaN values
            user_id = row.get(Config.ROSTER_COLS['user_id'], 'N/A')
            skills = str(row.get(Config.ROSTER_COLS['skills'], 'N/A'))
            on_call = 'Yes' if self._is_on_call(row) else 'No'
            max_concurrent = row.get(Config.ROSTER_COLS['max_concurrent'], 0)
            group = row.get(Config.ROSTER_COLS['group'], 'N/A')
            
            result.append({
                'user_id': user_id if not pd.isna(user_id) else 'N/A',
                'name': f"User_{user_id}" if not pd.isna(user_id) else 'N/A',
                'skills': skills,
                'on_call': on_call,
                'group': group,
                'max_concurrent': int(max_concurrent) if not pd.isna(max_concurrent) else 0,
                'score': row.get('total_score', 0)
            })
        
        return result
    
    def _is_on_call(self, person: pd.Series) -> bool:
        """Helper to check on-call status"""
        on_call_val = person.get(Config.ROSTER_COLS['on_call'], 'No')
        return str(on_call_val).lower() in ['yes', 'true', '1', 'y']
    
    def _merge_recommendations(self, llm_result: Dict, candidates: pd.DataFrame) -> Dict:
        """Merge LLM results with candidate data"""
        recommendations = {}
        
        # Get top 3 from LLM result
        for i in range(1, min(Config.TOP_K + 1, 4)):
            top_key = f'top{i}'
            if top_key in llm_result:
                recommendations[top_key] = llm_result[top_key]
        
        recommendations['overall_analysis'] = llm_result.get('overall_analysis', '')
        
        return recommendations

