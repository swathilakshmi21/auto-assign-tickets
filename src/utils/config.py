"""Configuration management"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM Configuration
    LLM_ENDPOINT = os.getenv('LLM_Wrapper_ENDPOINT')
    AZURE_OPENAI_KEY = os.getenv('AZURE_OPENAI_KEY')
    OPENAI_API_VERSION = os.getenv('OPENAI_API_VERSION', '2024-02-15-preview')
    DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'gpt-4-turbo-preview')
    
    # Assignment Configuration
    TOP_K = int(os.getenv('TOP_K_COUNT', 3))
    MIN_SCORE_THRESHOLD = int(os.getenv('MIN_SCORE_THRESHOLD', 40))
    
    # File Paths
    INPUT_DIR = "inputs"
    OUTPUT_DIR = "outputs"
    STORAGE_FILE = "outputs/assignments.xlsx"
    
    # Roster columns (MATCHING ACTUAL EXCEL STRUCTURE)
    ROSTER_COLS = {
        'user_id': 'user_id',
        'group': 'group',
        'skills': 'skills_csv',
        'shift_tz': 'shift_tz',
        'shift_start': 'shift_start',
        'shift_end': 'shift_end',
        'on_call': 'on_call',
        'max_concurrent': 'max_concurrent'
    }
    
    # Priority weights
    PRIORITY_WEIGHTS = {
        'P1': 100,
        'P2': 75,
        'P3': 50,
        'P4': 25
    }
    
    # ServiceNow Configuration
    SERVICENOW_ENABLED = os.getenv('SERVICENOW_ENABLED', 'false').lower() == 'true'
    SERVICENOW_INSTANCE_URL = os.getenv('SERVICENOW_INSTANCE_URL', '')
    SERVICENOW_USERNAME = os.getenv('SERVICENOW_USERNAME', '')
    SERVICENOW_PASSWORD = os.getenv('SERVICENOW_PASSWORD', '')
    
    # ServiceNow Table Names (as created by user)
    SERVICENOW_ROSTER_TABLE = os.getenv('SERVICENOW_ROSTER_TABLE', 'rosters')
    SERVICENOW_INCIDENTS_TABLE = os.getenv('SERVICENOW_INCIDENTS_TABLE', 'incidents_1s')
    SERVICENOW_ASSIGNMENTS_TABLE = os.getenv('SERVICENOW_ASSIGNMENTS_TABLE', 'assignments_trackings')
    SERVICENOW_WORKLOAD_TABLE = os.getenv('SERVICENOW_WORKLOAD_TABLE', 'workload_trackings')

