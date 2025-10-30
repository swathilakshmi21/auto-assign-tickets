"""Matching engine for incidents and roster with Indian timezone support"""
from typing import Dict, List
import pandas as pd
from datetime import datetime, time
import pytz
from ..utils.config import Config

class Matcher:
    def __init__(self, roster_df: pd.DataFrame, storage=None):
        self.roster_df = roster_df
        self.cols = Config.ROSTER_COLS
        self.storage = storage
        self.indian_tz = pytz.timezone('Asia/Kolkata')
    
    def find_candidates(self, incident: Dict) -> pd.DataFrame:
        """
        Find potential candidates based on incident requirements.
        Now includes workload capacity checking.
        
        Args:
            incident: Incident data
            
        Returns:
            DataFrame of potential candidates
        """
        candidates = self.roster_df.copy()
        
        # Filter by skill match
        subcategory = incident.get('subcategory', '').lower()
        if subcategory:
            def matches_skill(skills_csv):
                if pd.isna(skills_csv):
                    return False
                skills = [s.strip().lower() for s in str(skills_csv).split(',')]
                return subcategory in skills or any(subcategory in skill for skill in skills)
            
            skill_mask = candidates[self.cols['skills']].apply(matches_skill)
            candidates = candidates[skill_mask]
        
        # Filter by workload capacity if storage is available
        if self.storage is not None:
            def has_capacity(row):
                user_id = row[self.cols['user_id']]
                return self.storage.is_user_available(user_id, self.roster_df)
            
            capacity_mask = candidates.apply(has_capacity, axis=1)
            candidates = candidates[capacity_mask]
        
        return candidates
    
    def match_skill(self, incident_subcategory: str, skills_csv: str) -> bool:
        """Check if subcategory matches any skill"""
        if pd.isna(skills_csv) or not incident_subcategory:
            return False
        
        skills = [s.strip().lower() for s in str(skills_csv).split(',')]
        incident_sub = incident_subcategory.lower()
        
        # Exact match or partial match
        return any(incident_sub == skill or incident_sub in skill for skill in skills)
    
    def _check_shift_time(self, incident_time_str: str, person: pd.Series) -> bool:
        """
        Check if incident opened during person's shift using Indian timezone.
        
        Args:
            incident_time_str: Incident opened_at timestamp
            person: Person row from roster
            
        Returns:
            True if within shift, False otherwise
        """
        try:
            # Parse incident time
            if isinstance(incident_time_str, str):
                from dateutil import parser
                incident_time = parser.parse(incident_time_str)
            else:
                incident_time = pd.to_datetime(incident_time_str)
            
            # Convert to Indian timezone
            if incident_time.tzinfo is None:
                # Assume UTC if no timezone info
                incident_time = pytz.utc.localize(incident_time)
            
            incident_time_indian = incident_time.astimezone(self.indian_tz)
            
            # Get shift start/end
            shift_start = person[self.cols['shift_start']]
            shift_end = person[self.cols['shift_end']]
            
            if pd.isna(shift_start) or pd.isna(shift_end):
                return True  # No shift defined = always available
            
            # Parse shift times
            if isinstance(shift_start, str):
                try:
                    # Handle time-only strings (e.g., "09:00:00")
                    start_time = time.fromisoformat(str(shift_start)[:8])  # HH:MM:SS
                    end_time = time.fromisoformat(str(shift_end)[:8])
                    
                    # Create datetime objects for today in Indian timezone
                    today_indian = datetime.now(self.indian_tz).date()
                    start_datetime = self.indian_tz.localize(
                        datetime.combine(today_indian, start_time)
                    )
                    end_datetime = self.indian_tz.localize(
                        datetime.combine(today_indian, end_time)
                    )
                    
                    # Handle overnight shifts
                    if start_time < end_time:
                        # Normal shift (e.g., 9 AM to 6 PM)
                        return start_datetime <= incident_time_indian <= end_datetime
                    else:
                        # Overnight shift (e.g., 10 PM to 6 AM)
                        # Check if incident is after start time OR before end time
                        return (incident_time_indian >= start_datetime or 
                                incident_time_indian <= end_datetime)
                except ValueError:
                    return True
            
            return True  # If parsing fails, assume available
            
        except Exception as e:
            print(f"Error checking shift: {e}")
            return True  # Default to available
    
    def is_on_call(self, person: pd.Series) -> bool:
        """Check if person is on-call"""
        on_call_val = person.get(self.cols['on_call'], 'No')
        return str(on_call_val).lower() in ['yes', 'true', '1', 'y']
    
    def get_availability_message(self) -> str:
        """Get message about availability"""
        if self.storage is None:
            return "Workload tracking not available"
        
        # Count available people
        available_count = 0
        total_count = len(self.roster_df)
        
        for _, row in self.roster_df.iterrows():
            user_id = row[self.cols['user_id']]
            if self.storage.is_user_available(user_id, self.roster_df):
                available_count += 1
        
        if available_count == 0:
            return "❌ No persons are free to assign. All team members are at max capacity."
        else:
            return f"✅ {available_count} of {total_count} team members available for assignment."
