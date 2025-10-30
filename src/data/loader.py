"""Data loading from Excel files or ServiceNow"""
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional
from ..utils.config import Config
from .servicenow_client import ServiceNowClient

class DataLoader:
    def __init__(self, use_servicenow: bool = None, sn_client: Optional[ServiceNowClient] = None):
        self.input_dir = Path(Config.INPUT_DIR)
        self.use_servicenow = use_servicenow if use_servicenow is not None else Config.SERVICENOW_ENABLED
        self.sn_client = sn_client
        
        # Initialize ServiceNow client if needed
        if self.use_servicenow and not self.sn_client:
            try:
                self.sn_client = ServiceNowClient()
            except Exception as e:
                print(f"⚠️ Warning: ServiceNow client initialization failed: {e}")
                print("   Falling back to Excel file loading")
                self.use_servicenow = False
    
    def load_roster(self, filename: str = "dummy_roster_servicenow.xlsx") -> pd.DataFrame:
        """Load roster data from ServiceNow or Excel"""
        if self.use_servicenow and self.sn_client:
            try:
                print("📡 Loading roster from ServiceNow...")
                roster_df = self.sn_client.get_roster_data()
                if roster_df is not None and len(roster_df) > 0:
                    print(f"✓ Loaded roster from ServiceNow: {len(roster_df)} people")
                    return roster_df
                else:
                    print("⚠️ No roster data from ServiceNow, falling back to Excel")
            except Exception as e:
                print(f"⚠️ Error loading from ServiceNow: {e}")
                print("   Falling back to Excel")
        
        # Fallback to Excel
        filepath = self.input_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Roster file not found: {filepath}")
        
        roster_df = pd.read_excel(filepath)
        
        # Normalize column names (strip whitespace)
        roster_df.columns = roster_df.columns.str.strip()
        
        print(f"✓ Loaded roster from Excel: {len(roster_df)} people")
        return roster_df
    
    def load_incidents(self, filename: str = "incidents.xlsx") -> pd.DataFrame:
        """Load incidents data from ServiceNow or Excel"""
        if self.use_servicenow and self.sn_client:
            try:
                print("📡 Loading incidents from ServiceNow...")
                incidents_df = self.sn_client.get_incidents()
                if incidents_df is not None and len(incidents_df) > 0:
                    print(f"✓ Loaded incidents from ServiceNow: {len(incidents_df)} incidents")
                    return incidents_df
                else:
                    print("⚠️ No incidents from ServiceNow, falling back to Excel")
            except Exception as e:
                print(f"⚠️ Error loading from ServiceNow: {e}")
                print("   Falling back to Excel")
        
        # Fallback to Excel
        filepath = self.input_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Incidents file not found: {filepath}")
        
        incidents_df = pd.read_excel(filepath)
        
        # Normalize column names
        incidents_df.columns = incidents_df.columns.str.strip()
        
        # Ensure required columns exist
        required_cols = ['short_description', 'category', 'subcategory', 'priority', 'opened_at']
        missing = [col for col in required_cols if col not in incidents_df.columns]
        if missing:
            print(f"⚠️ Missing columns in incidents: {missing}")
        
        print(f"✓ Loaded incidents from Excel: {len(incidents_df)} incidents")
        return incidents_df
    
    def load_all(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load both roster and incidents"""
        roster_df = self.load_roster()
        incidents_df = self.load_incidents()
        return roster_df, incidents_df

