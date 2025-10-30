"""Main Streamlit application for Auto Ticket Assignment POC"""
import streamlit as st
import pandas as pd
import time
from pathlib import Path

from src.data.loader import DataLoader
from src.data.storage import Storage
from src.data.servicenow_client import ServiceNowClient
from src.agents import AssignmentAgent
from src.ui import home, assigner, audit, task_manager
from src.utils.config import Config

# Webhook file watcher setup
WEBHOOK_FLAG_FILE = Path("outputs/webhook_flag.txt")
WEBHOOK_INCIDENTS_FILE = Path("outputs/webhook_incidents.json")

# Page config
st.set_page_config(
    page_title="Auto Ticket Assignment - POC",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful UI
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .priority-p1 { 
        background-color: #ffebee; 
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #d32f2f;
    }
    .priority-p2 { 
        background-color: #fff3e0; 
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #f57c00;
    }
    .priority-p3 { 
        background-color: #fffde7; 
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #f9a825;
    }
    .priority-p4 { 
        background-color: #e8f5e9; 
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #388e3c;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'roster_df' not in st.session_state:
    st.session_state.roster_df = None
if 'incidents_df' not in st.session_state:
    st.session_state.incidents_df = None
if 'loader' not in st.session_state:
    st.session_state.loader = None
if 'sn_client' not in st.session_state:
    # Initialize ServiceNow client if enabled
    st.session_state.sn_client = None
    if Config.SERVICENOW_ENABLED:
        try:
            st.session_state.sn_client = ServiceNowClient()
            print("✓ ServiceNow client initialized")
        except Exception as e:
            print(f"⚠️ ServiceNow client initialization failed: {e}")
            st.session_state.sn_client = None

if 'storage' not in st.session_state:
    st.session_state.storage = Storage(
        use_servicenow=Config.SERVICENOW_ENABLED,
        sn_client=st.session_state.get('sn_client')
    )
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = {}

# Sidebar
with st.sidebar:
    st.title("🎫 Auto Assignment")
    st.markdown("---")
    st.markdown("### AI-Powered Ticket Assignment")
    st.markdown("""
    This POC demonstrates intelligent ticket assignment using:
    - **AI Agent** (LLM-based reasoning)
    - **Smart Matching** (Skills, Shift, On-call, Capacity)
    - **Human-in-the-Loop** (Accept or Override)
    - **Audit Trail** (Full tracking and metrics)
    """)
    st.markdown("---")
    
    # Webhook status indicator
    webhook_enabled = WEBHOOK_FLAG_FILE.exists()
    if webhook_enabled:
        try:
            flag_time = float(WEBHOOK_FLAG_FILE.read_text())
            flag_datetime = time.ctime(flag_time)
            st.success(f"🔄 Webhook Active\nLast update: {flag_datetime}")
        except:
            st.info("🔄 Webhook file exists")
    else:
        st.info("ℹ️ Webhook server not running")
    
    st.markdown("---")
    
    # Load data button
    if st.button("🔄 Reload Data", use_container_width=True):
        try:
            with st.spinner("Loading data..."):
                # Initialize loader with ServiceNow support
                loader = DataLoader(
                    use_servicenow=Config.SERVICENOW_ENABLED,
                    sn_client=st.session_state.get('sn_client')
                )
                st.session_state.loader = loader
                st.session_state.roster_df = loader.load_roster()
                st.session_state.incidents_df = loader.load_incidents()
                
                # Update storage with ServiceNow client
                st.session_state.storage.sn_client = st.session_state.get('sn_client')
                st.session_state.storage.use_servicenow = Config.SERVICENOW_ENABLED
                
                # Initialize agent with roster data and storage
                if st.session_state.roster_df is not None:
                    st.session_state.agent = AssignmentAgent(st.session_state.roster_df, st.session_state.storage)
                
                # Show data source
                data_source = "ServiceNow" if Config.SERVICENOW_ENABLED and st.session_state.sn_client else "Excel"
                st.success(f"✅ Data loaded from {data_source}!")
                st.rerun()
        except Exception as e:
            st.error(f"❌ Error loading data: {e}")
            st.exception(e)
    
    st.markdown("---")
    
    # Status
    if st.session_state.roster_df is not None:
        st.success("✅ Data Loaded")
        st.caption(f"Roster: {len(st.session_state.roster_df)} people")
        st.caption(f"Incidents: {len(st.session_state.incidents_df)} tickets")
    else:
        st.info("ℹ️ Click 'Reload Data' to start")

# Initialize webhook file watcher
if 'last_webhook_check' not in st.session_state:
    st.session_state.last_webhook_check = time.time()
    st.session_state.last_webhook_time = 0
    if WEBHOOK_FLAG_FILE.exists():
        try:
            st.session_state.last_webhook_time = float(WEBHOOK_FLAG_FILE.read_text())
        except:
            pass

# Check for webhook updates every 2 seconds
current_time = time.time()
if current_time - st.session_state.last_webhook_check >= 2:
    if WEBHOOK_FLAG_FILE.exists():
        try:
            webhook_time = float(WEBHOOK_FLAG_FILE.read_text())
            if webhook_time > st.session_state.last_webhook_time:
                # New webhook received - reload incidents from ServiceNow
                if Config.SERVICENOW_ENABLED and st.session_state.get('sn_client'):
                    try:
                        loader = DataLoader(
                            use_servicenow=True,
                            sn_client=st.session_state.get('sn_client')
                        )
                        st.session_state.incidents_df = loader.load_incidents()
                        st.session_state.last_webhook_time = webhook_time
                        print(f"✅ Reloaded incidents after webhook (timestamp: {webhook_time})")
                        st.rerun()
                    except Exception as e:
                        print(f"⚠️ Error reloading after webhook: {e}")
                else:
                    st.session_state.last_webhook_time = webhook_time
        except Exception as e:
            print(f"⚠️ Error reading webhook flag: {e}")
    
    st.session_state.last_webhook_check = current_time

# Main navigation
page = st.sidebar.selectbox(
    "Navigate", 
    ["🏠 Dashboard", "📝 Assign Tickets", "📋 Task Management", "📊 Audit & Analytics"],
    index=0
)

# Initialize agent if not already initialized and roster is available
if st.session_state.agent is None and st.session_state.roster_df is not None:
    st.session_state.agent = AssignmentAgent(st.session_state.roster_df, st.session_state.storage)

# Update agent's storage reference if it exists (in case storage was updated)
if st.session_state.agent is not None:
    st.session_state.agent.update_storage(st.session_state.storage)

# Route to pages
try:
    if page == "🏠 Dashboard":
        home.render(st.session_state.incidents_df, st.session_state.storage)
    elif page == "📝 Assign Tickets":
        assigner.render(st.session_state.roster_df, st.session_state.incidents_df, 
                       st.session_state.storage, st.session_state.agent)
    elif page == "📋 Task Management":
        task_manager.render(st.session_state.storage, st.session_state.roster_df)
    elif page == "📊 Audit & Analytics":
        audit.render(st.session_state.storage)
except Exception as e:
    st.error(f"Error: {e}")
    st.exception(e)
    
    # Show stack trace in expander
    with st.expander("Show Error Details"):
        st.exception(e)

