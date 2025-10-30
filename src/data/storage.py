"""Storage layer for assignments and audit data with workload tracking"""
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pytz
from ..utils.config import Config
import os

class Storage:
    def __init__(self, use_servicenow: bool = False, sn_client=None):
        self.storage_file = Path(Config.STORAGE_FILE)
        self.workload_file = Path(Config.OUTPUT_DIR) / "workload_tracking.xlsx"
        self.storage_file.parent.mkdir(exist_ok=True)
        
        # ServiceNow integration
        self.use_servicenow = use_servicenow if use_servicenow is not None else Config.SERVICENOW_ENABLED
        self.sn_client = sn_client
        
        # ServiceNow table names from Config
        self.sn_assignments_table = Config.SERVICENOW_ASSIGNMENTS_TABLE
        self.sn_workload_table = Config.SERVICENOW_WORKLOAD_TABLE
        self.sn_recommendations_table = os.getenv('SERVICENOW_RECOMMENDATIONS_TABLE', 'u_ai_recommendations')
        
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize storage files if they don't exist"""
        if not self.storage_file.exists():
            # Create empty DataFrame with columns
            columns = [
                'timestamp', 'incident_short_desc', 'category', 'subcategory', 
                'priority', 'opened_at', 'top1_recommended', 'top1_score',
                'selected_person', 'action', 'llm_explanation', 'time_saved_minutes',
                'top1_user_id', 'selected_user_id', 'assignment_id', 'status'
            ]
            df = pd.DataFrame(columns=columns)
            df.to_excel(self.storage_file, index=False)
        
        if not self.workload_file.exists():
            # Create workload tracking file
            workload_columns = [
                'assignment_id', 'user_id', 'incident_short_desc', 'priority',
                'assigned_at', 'closed_at', 'status', 'workload_count'
            ]
            df = pd.DataFrame(columns=workload_columns)
            df.to_excel(self.workload_file, index=False)
    
    def save_assignment(self, incident: Dict, recommendations: Dict, 
                       selected_person: str, action: str, selected_user_id: str = None) -> str:
        """
        Save assignment to Excel with full audit trail and workload tracking.
        
        Args:
            incident: Incident data
            recommendations: LLM recommendations
            selected_person: Person assigned (or "OVERRIDE-{name}")
            action: "Accept" or "Override"
            selected_user_id: Optional user ID if available
            
        Returns:
            assignment_id: Unique identifier for the assignment
        """
        assignment_id = f"ASSIGN_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{selected_user_id}"
        top1 = recommendations.get('top1', {})
        
        # Get current workload for this user
        current_workload = self.get_user_workload(selected_user_id)
        
        record = {
            'timestamp': datetime.now(),
            'incident_short_desc': incident.get('short_description', '')[:100],
            'category': incident.get('category', ''),
            'subcategory': incident.get('subcategory', ''),
            'priority': incident.get('priority', ''),
            'opened_at': incident.get('opened_at', ''),
            
            'top1_recommended': top1.get('name', 'N/A'),
            'top1_user_id': top1.get('user_id', 'N/A'),
            'top1_score': top1.get('recommendation_score', 0),
            
            'selected_person': selected_person,
            'selected_user_id': selected_user_id or 'N/A',
            'action': action,
            'assignment_id': assignment_id,
            'status': 'OPEN',
            
            'llm_explanation': recommendations.get('overall_analysis', ''),
            'time_saved_minutes': self._estimate_time_saved(action)
        }
        
        # Load existing data
        df = pd.read_excel(self.storage_file)
        
        # Append new record
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
        
        # Save to Excel (always, as backup)
        df.to_excel(self.storage_file, index=False)
        
        # Update workload tracking in Excel
        self._update_workload_tracking(assignment_id, selected_user_id, incident, 'OPEN')
        
        # Save to ServiceNow if enabled
        if self.use_servicenow:
            self._save_to_servicenow(assignment_id, incident, recommendations, selected_person, action, selected_user_id)
        
        print(f"✓ Saved assignment: {selected_person} (ID: {assignment_id})")
        return assignment_id
    
    def get_user_workload(self, user_id: str) -> int:
        """Get current open workload for a user"""
        # Try ServiceNow first if enabled
        if self.use_servicenow and self.sn_client:
            try:
                # Fetch assignments for this user from ServiceNow
                # ServiceNow query syntax: field=value^field2=value2 (^ is AND)
                assignments_df = self.sn_client.get_assignments(
                    query=f'selected_user_id={user_id}^status=OPEN'
                )
                if assignments_df is not None and len(assignments_df) > 0:
                    return len(assignments_df)
            except Exception as e:
                print(f"⚠️ Error getting workload from ServiceNow: {e}, falling back to Excel")
        
        # Fallback to Excel
        if not self.workload_file.exists():
            return 0
        
        df = pd.read_excel(self.workload_file)
        if len(df) == 0:
            return 0
        
        # Count open assignments for this user
        open_assignments = df[
            (df['user_id'] == user_id) & 
            (df['status'] == 'OPEN')
        ]
        
        return len(open_assignments)
    
    def get_user_max_concurrent(self, roster_df: pd.DataFrame, user_id: str) -> int:
        """Get max concurrent limit for a user from roster"""
        user_row = roster_df[roster_df['user_id'] == user_id]
        if len(user_row) == 0:
            return 0
        
        return user_row.iloc[0].get('max_concurrent', 0)
    
    def is_user_available(self, user_id: str, roster_df: pd.DataFrame) -> bool:
        """Check if user has capacity for new assignment"""
        current_workload = self.get_user_workload(user_id)
        max_concurrent = self.get_user_max_concurrent(roster_df, user_id)
        
        return current_workload < max_concurrent
    
    def get_all_open_assignments(self) -> pd.DataFrame:
        """Get all open assignments"""
        if not self.workload_file.exists():
            return pd.DataFrame()
        
        df = pd.read_excel(self.workload_file)
        return df[df['status'] == 'OPEN']
    
    def close_assignment(self, assignment_id: str) -> bool:
        """Close an assignment and update workload"""
        # Try ServiceNow first if enabled
        if self.use_servicenow and self.sn_client:
            try:
                # Find assignment by assignment_id
                assignments_df = self.sn_client.get_assignments(query=f'assignment_id={assignment_id}')
                if assignments_df is not None and len(assignments_df) > 0:
                    sys_id = assignments_df.iloc[0].get('sys_id')
                    if sys_id:
                        success = self.sn_client.update_assignment_status(sys_id, 'CLOSED')
                        if success:
                            # Also update Excel as backup
                            self._close_assignment_excel(assignment_id)
                            return True
            except Exception as e:
                print(f"⚠️ Error closing assignment in ServiceNow: {e}, falling back to Excel")
        
        # Fallback to Excel
        return self._close_assignment_excel(assignment_id)
    
    def _close_assignment_excel(self, assignment_id: str) -> bool:
        """Close assignment in Excel files"""
        if not self.workload_file.exists():
            return False
        
        df = pd.read_excel(self.workload_file)
        
        # Find the assignment
        assignment_mask = df['assignment_id'] == assignment_id
        if not assignment_mask.any():
            return False
        
        # Update status to CLOSED
        df.loc[assignment_mask, 'status'] = 'CLOSED'
        df.loc[assignment_mask, 'closed_at'] = datetime.now()
        
        # Save updated data
        df.to_excel(self.workload_file, index=False)
        
        # Also update main storage file
        if self.storage_file.exists():
            main_df = pd.read_excel(self.storage_file)
            main_df.loc[main_df['assignment_id'] == assignment_id, 'status'] = 'CLOSED'
            main_df.to_excel(self.storage_file, index=False)
        
        print(f"✓ Closed assignment: {assignment_id}")
        return True
    
    def _update_workload_tracking(self, assignment_id: str, user_id: str, incident: Dict, status: str):
        """Update workload tracking file"""
        if not self.workload_file.exists():
            self._initialize_storage()
        
        df = pd.read_excel(self.workload_file)
        
        # Calculate current workload count for this user
        current_workload = self.get_user_workload(user_id)
        if status == 'OPEN':
            workload_count = current_workload + 1
        else:
            workload_count = current_workload
        
        record = {
            'assignment_id': assignment_id,
            'user_id': user_id,
            'incident_short_desc': incident.get('short_description', '')[:100],
            'priority': incident.get('priority', ''),
            'assigned_at': datetime.now(),
            'closed_at': None if status == 'OPEN' else datetime.now(),
            'status': status,
            'workload_count': workload_count
        }
        
        # Append new record
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
        df.to_excel(self.workload_file, index=False)
    
    def get_statistics(self) -> Dict:
        """Get audit statistics including workload info"""
        if not self.storage_file.exists():
            return {
                'total_assignments': 0,
                'acceptance_rate': 0,
                'total_time_saved': 0,
                'policy_violations': 0,
                'reassignments': 0,
                'open_assignments': 0,
                'closed_assignments': 0
            }
        
        df = pd.read_excel(self.storage_file)
        
        if len(df) == 0:
            return {
                'total_assignments': 0,
                'acceptance_rate': 0,
                'total_time_saved': 0,
                'policy_violations': 0,
                'reassignments': 0,
                'open_assignments': 0,
                'closed_assignments': 0
            }
        
        total = len(df)
        accepts = len(df[df['action'] == 'Accept'])
        open_count = len(df[df['status'] == 'OPEN']) if 'status' in df.columns else 0
        closed_count = len(df[df['status'] == 'CLOSED']) if 'status' in df.columns else 0
        
        return {
            'total_assignments': total,
            'acceptance_rate': (accepts / total * 100) if total > 0 else 0,
            'total_time_saved': df['time_saved_minutes'].sum(),
            'policy_violations': 0,  # TODO: Implement violation detection
            'reassignments': 0,  # TODO: Track reassignments
            'open_assignments': open_count,
            'closed_assignments': closed_count
        }
    
    def get_all_assignments(self) -> pd.DataFrame:
        """Get all assignment history"""
        # Try ServiceNow first if enabled
        if self.use_servicenow and self.sn_client:
            try:
                assignments_df = self.sn_client.get_assignments()
                if assignments_df is not None and len(assignments_df) > 0:
                    return assignments_df
            except Exception as e:
                print(f"⚠️ Error getting assignments from ServiceNow: {e}, falling back to Excel")
        
        # Fallback to Excel
        if not self.storage_file.exists():
            return pd.DataFrame()
        
        return pd.read_excel(self.storage_file)
    
    def _estimate_time_saved(self, action: str) -> float:
        """Estimate time saved (in minutes)"""
        # Accept saves ~10 minutes, Override saves ~5 minutes
        return 10.0 if action == 'Accept' else 5.0
    
    # ServiceNow Integration Methods
    def _save_to_servicenow(self, assignment_id: str, incident: Dict, recommendations: Dict, 
                            selected_person: str, action: str, selected_user_id: str) -> bool:
        """Save assignment to ServiceNow tables"""
        if not self.use_servicenow or not self.sn_client:
            return False
        
        try:
            top1 = recommendations.get('top1', {})
            
            # Prepare data for u_ticket_assignments table
            assignment_data = {
                'assignment_id': assignment_id,
                'incident_short_desc': incident.get('short_description', '')[:160],
                'incident_description': incident.get('description', ''),
                'category': incident.get('category', ''),
                'subcategory': incident.get('subcategory', ''),
                'priority': incident.get('priority', ''),
                'opened_at': incident.get('opened_at', ''),
                'top1_recommended': top1.get('name', 'N/A'),
                'top1_recommended_user_id': top1.get('user_id', 'N/A'),
                'top1_score': int(top1.get('recommendation_score', 0)),
                'selected_person': selected_person,
                'selected_user_id': selected_user_id or 'N/A',
                'action': action,
                'status': 'OPEN',
                'llm_explanation': recommendations.get('overall_analysis', ''),
                'time_saved_minutes': int(self._estimate_time_saved(action)),
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'AI_Assignment_System'
            }
            
            # Save to assignments table
            self.sn_client.create_assignment_record(assignment_data)
            
            # Save recommendations to u_ai_recommendations table
            self._save_recommendations_to_sn(assignment_id, recommendations)
            
            # Update workload tracking
            self._update_workload_in_sn(assignment_id, selected_user_id, incident, 'OPEN')
            
            return True
            
        except Exception as e:
            print(f"Error saving to ServiceNow: {e}")
            return False
    
    def _save_recommendations_to_sn(self, assignment_id: str, recommendations: Dict):
        """Save AI recommendations to ServiceNow"""
        if not self.use_servicenow or not self.sn_client:
            return
        
        try:
            rec_data = {
                'assignment_id': assignment_id,
                'top1_name': recommendations.get('top1', {}).get('name', ''),
                'top1_user_id': recommendations.get('top1', {}).get('user_id', ''),
                'top1_score': int(recommendations.get('top1', {}).get('recommendation_score', 0)),
                'top1_reasons': '\n'.join(recommendations.get('top1', {}).get('reasons', [])),
                'top2_name': recommendations.get('top2', {}).get('name', ''),
                'top2_user_id': recommendations.get('top2', {}).get('user_id', ''),
                'top2_score': int(recommendations.get('top2', {}).get('recommendation_score', 0)),
                'top3_name': recommendations.get('top3', {}).get('name', ''),
                'top3_user_id': recommendations.get('top3', {}).get('user_id', ''),
                'top3_score': int(recommendations.get('top3', {}).get('recommendation_score', 0)),
                'overall_analysis': recommendations.get('overall_analysis', ''),
                'recommendation_timestamp': datetime.now().isoformat()
            }
            
            # Save recommendations to recommendations table (if exists)
            if hasattr(self.sn_client, 'create_assignment_record'):
                self.sn_client.create_assignment_record(rec_data, table_name=self.sn_recommendations_table)
            
        except Exception as e:
            print(f"Error saving recommendations to ServiceNow: {e}")
    
    def _update_workload_in_sn(self, assignment_id: str, user_id: str, incident: Dict, status: str):
        """Update workload tracking in ServiceNow"""
        if not self.use_servicenow or not self.sn_client:
            return
        
        try:
            workload_data = {
                'assignment_id': assignment_id,
                'incident_short_desc': incident.get('short_description', '')[:160],
                'priority': incident.get('priority', ''),
                'status': status,
                'assigned_at': datetime.now().isoformat(),
                'workload_count': self.get_user_workload(user_id)
            }
            
            self.sn_client.update_workload(user_id, workload_data)
            
        except Exception as e:
            print(f"Error updating workload in ServiceNow: {e}")
