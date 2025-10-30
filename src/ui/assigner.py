"""Assignment interface page"""
import streamlit as st
import pandas as pd
from typing import Optional
from src.core.matcher import Matcher
from src.core.scorer import Scorer
from src.core.reasoner import Reasoner
from src.utils.llm_client import LLMClient
from src.utils.config import Config

def _get_assigned_incidents(storage):
    """Get list of incident descriptions that have been assigned"""
    assigned = set()
    
    try:
        # Get all assignments from storage
        assignments = storage.get_all_assignments()
        
        if len(assignments) > 0:
            for _, row in assignments.iterrows():
                incident_desc = row.get('incident_short_desc', '')
                if incident_desc:
                    assigned.add(incident_desc)
    except Exception as e:
        print(f"Error getting assigned incidents: {e}")
    
    return assigned

def _filter_unassigned(incidents_df, assigned_incidents):
    """Filter incidents to only show unassigned ones"""
    if len(assigned_incidents) == 0:
        return incidents_df
    
    # Filter out incidents that have been assigned
    mask = incidents_df.apply(
        lambda row: row.get('short_description', '') not in assigned_incidents,
        axis=1
    )
    
    return incidents_df[mask].copy()

def render(roster_df, incidents_df, storage, agent=None):
    st.title("📝 Assign Tickets")
    st.markdown("---")
    
    if incidents_df is None or len(incidents_df) == 0:
        st.warning("⚠️ No incidents available to assign.")
        return
    
    if roster_df is None or len(roster_df) == 0:
        st.error("❌ No roster data available.")
        return
    
    # Check if agent is available
    if agent is None:
        st.error("❌ AI Agent not initialized. Please reload data.")
        return
    
    # Get list of already assigned incidents
    assigned_incidents = _get_assigned_incidents(storage)
    
    # Filter out already assigned incidents
    unassigned_incidents = _filter_unassigned(incidents_df, assigned_incidents)
    
    if len(unassigned_incidents) == 0:
        st.info("🎉 All incidents have been assigned!")
        return
    
    # Show count of unassigned vs total
    total_count = len(incidents_df)
    unassigned_count = len(unassigned_incidents)
    assigned_count = total_count - unassigned_count
    
    if assigned_count > 0:
        st.info(f"📊 {unassigned_count} unassigned / {total_count} total incidents ({assigned_count} already assigned)")
    
    # Select incident from unassigned only
    incident_options = [
        f"{idx}: {row['short_description'][:50]} - {row.get('priority', 'P3')}"
        for idx, row in unassigned_incidents.iterrows()
    ]
    selected = st.selectbox("Select Incident", incident_options, key="incident_selector")
    
    selected_idx = int(selected.split(':')[0])
    incident = unassigned_incidents.loc[selected_idx].to_dict()
    
    # Display incident details with styling
    st.markdown("### 📋 Incident Details")
    
    # Priority-based color
    priority_colors = {
        'P1': '🔴 P1 - Critical',
        'P2': '🟠 P2 - High',
        'P3': '🟡 P3 - Medium',
        'P4': '🟢 P4 - Low'
    }
    priority_label = priority_colors.get(incident.get('priority', 'P3'), '⚪ Unknown')
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**Priority:** {priority_label}")
    with col2:
        st.info(f"**Category:** {incident.get('category', 'N/A')}")
    with col3:
        st.info(f"**Subcategory:** {incident.get('subcategory', 'N/A')}")
    
    st.text_area("Short Description", incident.get('short_description', 'N/A'), 
                 height=80, disabled=True)
    
    st.text_area("Description", incident.get('description', 'N/A'), 
                 height=100, disabled=True)
    
    st.markdown("---")
    
    # Generate recommendations button
    if st.button("🔍 Generate AI Recommendations", type="primary", use_container_width=True):
        with st.spinner("🤖 AI Agent analyzing..."):
            try:
                # Use the agent to generate recommendations
                result = agent.recommend_assignees(incident)
                
                # Check if no candidates found
                if 'error' in result:
                    st.error(f"❌ {result['error']}")
                    if 'overall_analysis' in result:
                        st.info(f"💡 {result['overall_analysis']}")
                    return
                
                # Store results in session
                st.session_state['current_incident'] = incident
                st.session_state['recommendations'] = result.get('recommendations', {})
                st.session_state['candidates'] = result.get('candidates', pd.DataFrame())
                st.session_state['agent_method'] = result.get('agent_method', 'unknown')
                
                # Show success message with agent method
                method_display = "LLM Reasoning" if result.get('agent_method') == 'llm_reasoning' else "Score-Based Fallback"
                st.success(f"✅ Recommendations generated using {method_display}!")
                
            except Exception as e:
                st.error(f"❌ Error generating recommendations: {str(e)}")
                st.exception(e)
    
    # Display recommendations
    if 'recommendations' in st.session_state and st.session_state.get('recommendations'):
        recommendations = st.session_state.get('recommendations', {})
        
        if not isinstance(recommendations, dict):
            st.error("Invalid recommendations format")
        else:
            st.markdown("### 🤖 AI Recommendations (Top " + str(Config.TOP_K) + ")")
            
            priority = incident.get('priority', 'P3')
            priority_class = priority.lower() if priority else 'p3'
            
            for i in range(1, min(Config.TOP_K + 1, 4)):
                top_key = f'top{i}'
                if top_key not in recommendations:
                    continue
                
                rec = recommendations.get(top_key)
                if rec is None:
                    continue
                
                user_id = rec.get('user_id', 'N/A')
                
                with st.container():
                    st.markdown(f"#### 👤 {rec.get('name', 'Unknown')} (ID: {user_id})")
                    
                    # Score badge
                    score = rec.get('recommendation_score', 0)
                    if score >= 80:
                        score_color = "✅"
                    elif score >= 60:
                        score_color = "⚠️"
                    else:
                        score_color = "❌"
                    
                    st.markdown(f"{score_color} **Recommendation Score:** {score}/100")
                    
                    # Reasons
                    if 'reasons' in rec:
                        st.markdown("**Key Reasons:**")
                        for reason in rec['reasons'][:3]:
                            st.markdown(f"- {reason}")
                    
                    # Explanation
                    if 'explanation' in rec:
                        st.markdown(f"💡 {rec['explanation']}")
                    
                    # Action buttons
                    col_btn1, col_btn2 = st.columns([3, 1])
                    
                    with col_btn1:
                        if st.button(f"✅ Accept & Assign to {rec.get('name', 'User')}", 
                                    key=f"accept_{i}"):
                            # Save assignment
                            try:
                                storage.save_assignment(
                                    st.session_state.get('current_incident', {}),
                                    recommendations,
                                    rec.get('name', 'Unknown'),
                                    "Accept",
                                    user_id
                                )
                                st.success(f"✅ Successfully assigned to {rec.get('name', 'Unknown')}!")
                                st.balloons()
                                # Clear recommendations to prevent duplicates
                                if 'recommendations' in st.session_state:
                                    del st.session_state['recommendations']
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error saving assignment: {e}")
                    
                    st.markdown("---")
            
            # Manual Override section
            st.markdown("### 🔄 Manual Override")
            
            # Get unique users from roster
            if 'user_id' in roster_df.columns:
                user_options = []
                for idx, row in roster_df.iterrows():
                    user_id = row.get('user_id', 'N/A')
                    group = row.get('group', 'N/A')
                    user_options.append(f"{user_id} ({group})")
                
                override_selection = st.selectbox(
                    "Select Alternate Assignee",
                    user_options,
                    key="override_selector"
                )
                
                if override_selection:
                    override_user_id = override_selection.split(' ')[0]
                    
                    if st.button("Assign via Override", type="secondary"):
                        try:
                            storage.save_assignment(
                                st.session_state.get('current_incident', {}),
                                recommendations,
                                f"OVERRIDE-{override_user_id}",
                                "Override",
                                override_user_id
                            )
                            st.success(f"✅ Override: Assigned to User ID {override_user_id}!")
                            st.balloons()
                            # Clear recommendations
                            if 'recommendations' in st.session_state:
                                del st.session_state['recommendations']
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error saving assignment: {e}")

