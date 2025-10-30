"""ServiceNow API integration for roster and incidents"""
import requests
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
import os
from ..utils.config import Config

class ServiceNowClient:
    """
    ServiceNow API client for fetching roster and incident data.
    """
    
    def __init__(self, instance_url: str = None, username: str = None, password: str = None):
        """
        Initialize ServiceNow client.
        
        Args:
            instance_url: ServiceNow instance URL (defaults to Config)
            username: ServiceNow username (defaults to Config)
            password: ServiceNow password (defaults to Config)
        """
        self.instance_url = (instance_url or Config.SERVICENOW_INSTANCE_URL).rstrip('/')
        self.username = username or Config.SERVICENOW_USERNAME
        self.password = password or Config.SERVICENOW_PASSWORD
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.auth = (self.username, self.password)
        
        if not all([self.instance_url, self.username, self.password]):
            raise ValueError("ServiceNow credentials not fully configured. Check .env file.")
    
    def get_roster_data(self, table_name: str = None) -> pd.DataFrame:
        """
        Fetch roster data from ServiceNow custom table.
        
        Args:
            table_name: Name of the custom table (defaults to Config.SERVICENOW_ROSTER_TABLE)
            
        Returns:
            DataFrame with roster data
        """
        table_name = table_name or Config.SERVICENOW_ROSTER_TABLE
        url = f"{self.instance_url}/api/now/table/{table_name}"
        
        # Build query parameters
        params = {
            'sysparm_query': 'active=true',  # Get active records only
            'sysparm_fields': 'sys_id,user_id,group,skills_csv,shift_tz,shift_start,shift_end,on_call,max_concurrent',
            'sysparm_limit': 1000  # Adjust as needed
        }
        
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data and 'result' in data:
                records = data['result']
                
                # Convert to DataFrame
                df = pd.DataFrame(records)
                
                # Normalize column names
                df.columns = df.columns.str.strip()
                
                print(f"✓ Loaded {len(df)} roster records from ServiceNow")
                return df
            else:
                print("⚠️ No roster data found in ServiceNow")
                return pd.DataFrame()
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching roster from ServiceNow: {e}")
            raise
    
    def get_incidents(self, incident_query: str = None, table_name: str = None) -> pd.DataFrame:
        """
        Fetch incident data from ServiceNow custom table.
        
        Args:
            incident_query: Optional query string (e.g., 'state=1') for filtering
            table_name: Name of the custom table (defaults to Config.SERVICENOW_INCIDENTS_TABLE)
            
        Returns:
            DataFrame with incident data
        """
        table_name = table_name or Config.SERVICENOW_INCIDENTS_TABLE
        url = f"{self.instance_url}/api/now/table/{table_name}"
        
        # Build query parameters
        query = incident_query or 'state!=6'  # Exclude closed incidents by default
        params = {
            'sysparm_query': query,
            'sysparm_fields': 'sys_id,short_description,description,category,subcategory,priority,cmdb_ci,opened_at',
            'sysparm_limit': 100  # Adjust as needed
        }
        
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data and 'result' in data:
                records = data['result']
                
                # Convert to DataFrame - use records directly or map as needed
                # Handle both custom table format and standard incident format
                if records:
                    # Check if records are in custom table format or standard format
                    df = pd.DataFrame(records)
                    df.columns = df.columns.str.strip()
                    
                    # Ensure priority is in P1-P4 format if it's numeric
                    if 'priority' in df.columns:
                        df['priority'] = df['priority'].apply(self._map_priority_if_needed)
                else:
                    df = pd.DataFrame()
                
                print(f"✓ Loaded {len(df)} incidents from ServiceNow")
                return df
            else:
                print("⚠️ No incidents found in ServiceNow")
                return pd.DataFrame()
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching incidents from ServiceNow: {e}")
            raise
    
    def _map_priority(self, priority: str) -> str:
        """Map ServiceNow priority codes to P1-P4 format"""
        priority_map = {
            '1': 'P1',  # Critical
            '2': 'P2',  # High
            '3': 'P3',  # Medium
            '4': 'P4'   # Low
        }
        return priority_map.get(str(priority), 'P3')
    
    def _map_priority_if_needed(self, priority_value):
        """Map priority only if it's numeric, otherwise return as-is"""
        if isinstance(priority_value, (int, float)):
            return self._map_priority(str(int(priority_value)))
        elif isinstance(priority_value, str):
            # If already in P1-P4 format, return as-is
            if priority_value.upper().startswith('P'):
                return priority_value.upper()
            # Otherwise map it
            return self._map_priority(priority_value)
        return priority_value
    
    def create_assignment_record(self, assignment_data: Dict, table_name: str = None) -> str:
        """
        Create a new assignment record in ServiceNow custom table.
        
        Args:
            assignment_data: Dictionary with assignment data
            table_name: Name of the custom table (defaults to Config.SERVICENOW_ASSIGNMENTS_TABLE)
            
        Returns:
            sys_id of created record
        """
        table_name = table_name or Config.SERVICENOW_ASSIGNMENTS_TABLE
        url = f"{self.instance_url}/api/now/table/{table_name}"
        
        try:
            response = requests.post(url, auth=self.auth, headers=self.headers, json=assignment_data)
            response.raise_for_status()
            
            result = response.json()
            sys_id = result.get('result', {}).get('sys_id', '')
            
            print(f"✓ Created assignment record: {sys_id}")
            return sys_id
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error creating assignment record: {e}")
            raise
    
    def update_workload(self, user_id: str, workload_data: Dict, table_name: str = None) -> bool:
        """
        Update workload tracking in ServiceNow.
        
        Args:
            user_id: User ID
            workload_data: Workload information
            table_name: Name of workload tracking table (defaults to Config.SERVICENOW_WORKLOAD_TABLE)
            
        Returns:
            True if successful
        """
        table_name = table_name or Config.SERVICENOW_WORKLOAD_TABLE
        url = f"{self.instance_url}/api/now/table/{table_name}"
        
        # Add user_id to workload data if not present
        if 'user_id' not in workload_data:
            workload_data['user_id'] = user_id
        
        # Add/update timestamp
        workload_data['last_updated'] = datetime.now().isoformat()
        
        try:
            # First try to find existing record for this user
            existing_record = self._find_workload_record(user_id, table_name)
            
            if existing_record:
                # Update existing record
                sys_id = existing_record.get('sys_id')
                update_url = f"{url}/{sys_id}"
                response = requests.put(update_url, auth=self.auth, headers=self.headers, json=workload_data)
            else:
                # Create new record
                response = requests.post(url, auth=self.auth, headers=self.headers, json=workload_data)
            
            response.raise_for_status()
            print(f"✓ Updated workload for user {user_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error updating workload: {e}")
            return False
    
    def _find_workload_record(self, user_id: str, table_name: str) -> Optional[Dict]:
        """Find existing workload record for a user"""
        url = f"{self.instance_url}/api/now/table/{table_name}"
        params = {
            'sysparm_query': f'user_id={user_id}',
            'sysparm_limit': 1
        }
        
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get('result'):
                return data['result'][0]
        except:
            pass
        return None
    
    def get_assignments(self, query: str = None, table_name: str = None) -> pd.DataFrame:
        """
        Fetch assignment records from ServiceNow.
        
        Args:
            query: Optional query string
            table_name: Table name (defaults to Config.SERVICENOW_ASSIGNMENTS_TABLE)
            
        Returns:
            DataFrame with assignment data
        """
        table_name = table_name or Config.SERVICENOW_ASSIGNMENTS_TABLE
        url = f"{self.instance_url}/api/now/table/{table_name}"
        
        params = {
            'sysparm_query': query or '',
            'sysparm_limit': 1000
        }
        
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data and 'result' in data:
                df = pd.DataFrame(data['result'])
                df.columns = df.columns.str.strip()
                return df
            return pd.DataFrame()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching assignments: {e}")
            return pd.DataFrame()
    
    def update_assignment_status(self, sys_id: str, status: str, table_name: str = None) -> bool:
        """
        Update assignment status.
        
        Args:
            sys_id: ServiceNow sys_id of the assignment record
            status: New status (e.g., 'CLOSED')
            table_name: Table name (defaults to Config.SERVICENOW_ASSIGNMENTS_TABLE)
            
        Returns:
            True if successful
        """
        table_name = table_name or Config.SERVICENOW_ASSIGNMENTS_TABLE
        url = f"{self.instance_url}/api/now/table/{table_name}/{sys_id}"
        
        update_data = {
            'status': status,
            'closed_at' if status == 'CLOSED' else 'updated': datetime.now().isoformat()
        }
        
        try:
            response = requests.put(url, auth=self.auth, headers=self.headers, json=update_data)
            response.raise_for_status()
            print(f"✓ Updated assignment {sys_id} to {status}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Error updating assignment status: {e}")
            return False

