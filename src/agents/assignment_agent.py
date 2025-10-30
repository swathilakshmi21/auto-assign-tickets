"""AI Agent for ticket assignment"""
from typing import Dict, List
import pandas as pd
from ..core.matcher import Matcher
from ..core.scorer import Scorer
from ..core.reasoner import Reasoner
from ..utils.llm_client import LLMClient
from ..utils.config import Config

class AssignmentAgent:
    """
    Main AI Agent that orchestrates the assignment process.
    This is where the 'agentic' behavior happens - minimal human intervention.
    """
    
    def __init__(self, roster_df: pd.DataFrame, storage=None):
        """
        Initialize the assignment agent.
        
        Args:
            roster_df: Roster DataFrame
            storage: Storage instance for workload tracking (optional)
        """
        self.roster_df = roster_df
        self.matcher = Matcher(roster_df, storage)
        self.scorer = Scorer(self.matcher)
        
        try:
            self.llm_client = LLMClient()
            self.reasoner = Reasoner(self.llm_client)
        except Exception as e:
            print(f"Warning: LLM client initialization failed: {e}")
            print("Agent will use fallback scoring only")
            self.llm_client = None
            self.reasoner = None
    
    def recommend_assignees(self, incident: Dict, top_k: int = None) -> Dict:
        """
        Get AI-powered recommendations for an incident.
        This is the main agent method that:
        1. Finds candidates
        2. Scores them
        3. Uses LLM to reason and provide explanations
        4. Returns Top-K recommendations
        
        Args:
            incident: Incident data dictionary
            top_k: Number of top recommendations (default: Config.TOP_K)
            
        Returns:
            Dictionary with recommendations and explanations
        """
        if top_k is None:
            top_k = Config.TOP_K
        
        # Step 1: Find candidates
        candidates = self.matcher.find_candidates(incident)
        
        if len(candidates) == 0:
            return self._no_candidates_response()
        
        # Step 2: Calculate scores
        scored_candidates = self.scorer.calculate_scores(incident, candidates)
        
        # Step 3: Get top-K
        top_candidates = scored_candidates.head(top_k)
        
        # Step 4: LLM reasoning (if available)
        if self.reasoner:
            recommendations = self.reasoner.generate_recommendations(incident, top_candidates)
        else:
            # Fallback to score-based recommendations
            recommendations = self._create_fallback_recommendations(top_candidates)
        
        return {
            'incident': incident,
            'recommendations': recommendations,
            'candidates': top_candidates,
            'agent_method': 'llm_reasoning' if self.reasoner else 'score_based'
        }
    
    def _create_fallback_recommendations(self, candidates: pd.DataFrame) -> Dict:
        """Create recommendations without LLM"""
        result = {}
        
        for i, (idx, row) in enumerate(candidates.iterrows(), 1):
            if i > 3:
                break
            
            user_id = row.get(Config.ROSTER_COLS['user_id'], 'N/A')
            
            result[f'top{i}'] = {
                'name': f"User_{user_id}",
                'user_id': user_id,
                'recommendation_score': int(row.get('total_score', 0)),
                'primary_reason': 'score_based',
                'reasons': [
                    f"Skill match score: {row.get('skill_score', 0)}",
                    f"On-call: {row.get(Config.ROSTER_COLS['on_call'], 'No')}",
                    f"Availability score: {row.get('availability_score', 0)}"
                ],
                'explanation': f"Ranked {i} based on combined scoring algorithm"
            }
        
        result['overall_analysis'] = "Recommendations based on algorithmic scoring (LLM unavailable)"
        return result
    
    def _no_candidates_response(self) -> Dict:
        """Response when no candidates found"""
        # Try to get a more specific error message from matcher
        error_msg = 'No suitable candidates found'
        analysis = 'No candidates match the incident requirements. Check skill matching.'
        
        try:
            if hasattr(self.matcher, 'get_availability_message'):
                availability_msg = self.matcher.get_availability_message()
                if availability_msg:
                    error_msg = availability_msg
                    analysis = 'No candidates available based on workload capacity or other constraints.'
        except:
            pass
        
        return {
            'error': error_msg,
            'recommendations': {},
            'overall_analysis': analysis
        }
    
    def update_storage(self, storage):
        """Update the storage instance for workload tracking"""
        self.matcher.storage = storage

