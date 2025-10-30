"""Scoring engine for ranking candidates with workload consideration"""
import pandas as pd
from typing import Dict
from .matcher import Matcher
from ..utils.config import Config

class Scorer:
    def __init__(self, matcher: Matcher):
        self.matcher = matcher
        self.cols = Config.ROSTER_COLS
    
    def calculate_scores(self, incident: Dict, candidates: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate scores for all candidates.
        Now includes current workload consideration.
        
        Args:
            incident: Incident data
            candidates: DataFrame of candidates
            
        Returns:
            DataFrame with scores added
        """
        candidates = candidates.copy()
        
        # Calculate skill match score
        candidates['skill_score'] = candidates.apply(
            lambda row: self._get_skill_score(row, incident), axis=1
        )
        
        # Calculate on-call boost
        candidates['oncall_score'] = candidates.apply(
            lambda row: self._get_oncall_score(row, incident), axis=1
        )
        
        # Calculate shift timing score
        candidates['shift_score'] = candidates.apply(
            lambda row: self._get_shift_score(row, incident), axis=1
        )
        
        # Calculate availability score (based on current workload vs max_concurrent)
        candidates['availability_score'] = candidates.apply(
            lambda row: self._get_availability_score(row, incident), axis=1
        )
        
        # Total score
        candidates['total_score'] = (
            candidates['skill_score'] +
            candidates['oncall_score'] +
            candidates['shift_score'] +
            candidates['availability_score']
        )
        
        # Sort by total score
        candidates = candidates.sort_values('total_score', ascending=False)
        
        return candidates
    
    def _get_skill_score(self, person: pd.Series, incident: Dict) -> float:
        """Calculate skill match score"""
        subcategory = incident.get('subcategory', '').lower()
        skills_csv = person[self.cols['skills']]
        
        if self.matcher.match_skill(subcategory, str(skills_csv)):
            # Exact match gets full points
            skills_list = [s.strip().lower() for s in str(skills_csv).split(',')]
            if subcategory in [s.strip().lower() for s in skills_list]:
                return 50
            else:
                # Partial match
                return 30
        return 0
    
    def _get_oncall_score(self, person: pd.Series, incident: Dict) -> float:
        """Calculate on-call boost"""
        if self.matcher.is_on_call(person):
            priority = incident.get('priority', 'P3')
            
            # Higher boost for higher priority incidents
            priority_boost = {
                'P1': 40,
                'P2': 30,
                'P3': 20,
                'P4': 10
            }.get(priority.upper(), 10)
            
            return 50 + priority_boost
        
        return 0
    
    def _get_shift_score(self, person: pd.Series, incident: Dict) -> float:
        """Calculate shift timing score"""
        incident_time_str = incident.get('opened_at', None)
        
        if not incident_time_str:
            return 20  # Neutral score
        
        if self.matcher._check_shift_time(incident_time_str, person):
            return 30  # Within shift
        else:
            return 0  # Outside shift (but still candidate)
    
    def _get_availability_score(self, person: pd.Series, incident: Dict) -> float:
        """Calculate availability based on current workload vs max_concurrent"""
        max_concurrent = person.get(self.cols['max_concurrent'], 0)
        
        if pd.isna(max_concurrent):
            return 10  # Unknown capacity
        
        # Get current workload if storage is available
        if self.matcher.storage is not None:
            user_id = person[self.cols['user_id']]
            current_workload = self.matcher.storage.get_user_workload(user_id)
            
            # Calculate capacity ratio
            if max_concurrent > 0:
                capacity_ratio = (max_concurrent - current_workload) / max_concurrent
                
                # Score based on available capacity
                if capacity_ratio >= 0.5:  # 50%+ capacity available
                    return 30
                elif capacity_ratio >= 0.25:  # 25%+ capacity available
                    return 20
                elif capacity_ratio > 0:  # Some capacity available
                    return 10
                else:
                    return 0  # No capacity (shouldn't happen due to filtering)
            else:
                return 5  # No max_concurrent defined
        else:
            # Fallback to max_concurrent only
            if max_concurrent >= 10:
                return 30
            elif max_concurrent >= 5:
                return 20
            elif max_concurrent >= 3:
                return 10
            else:
                return 5

