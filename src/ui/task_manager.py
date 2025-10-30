"""Task Management UI page"""
import streamlit as st
import pandas as pd
from datetime import datetime
import pytz

def render(storage, roster_df):
    st.title("📋 Task Management")
    st.markdown("---")
    
    # Get all open assignments
    open_assignments = storage.get_all_open_assignments()
    
    if len(open_assignments) == 0:
        st.info("No open assignments found.")
        return
    
    st.markdown(f"### 📊 Open Assignments ({len(open_assignments)})")
    
    # Display workload summary
    workload_summary = {}
    for _, assignment in open_assignments.iterrows():
        user_id = assignment['user_id']
        if user_id not in workload_summary:
            workload_summary[user_id] = 0
        workload_summary[user_id] += 1
    
    # Show workload by user
    st.markdown("#### Current Workload by User")
    col1, col2 = st.columns(2)
    
    with col1:
        for user_id, count in workload_summary.items():
            # Get max concurrent from roster
            user_row = roster_df[roster_df['user_id'] == user_id]
            if len(user_row) > 0:
                max_concurrent = user_row.iloc[0].get('max_concurrent', 0)
                group = user_row.iloc[0].get('group', 'N/A')
                
                # Color code based on capacity
                if count >= max_concurrent:
                    color = "🔴"
                elif count >= max_concurrent * 0.8:
                    color = "🟡"
                else:
                    color = "🟢"
                
                st.markdown(f"{color} **User {user_id}** ({group}): {count}/{max_concurrent}")
    
    with col2:
        # Overall stats
        total_open = len(open_assignments)
        total_users = len(workload_summary)
        avg_workload = total_open / total_users if total_users > 0 else 0
        
        st.metric("Total Open Tasks", total_open)
        st.metric("Active Users", total_users)
        st.metric("Avg Workload", f"{avg_workload:.1f}")
    
    st.markdown("---")
    
    # Display assignments table
    st.markdown("#### Assignment Details")
    
    # Add columns for better display
    display_df = open_assignments.copy()
    
    # Format datetime columns
    if 'assigned_at' in display_df.columns:
        display_df['assigned_at'] = pd.to_datetime(display_df['assigned_at']).dt.strftime('%Y-%m-%d %H:%M')
    
    # Add user info from roster
    user_info = {}
    for _, row in roster_df.iterrows():
        user_info[row['user_id']] = {
            'group': row.get('group', 'N/A'),
            'skills': row.get('skills_csv', 'N/A'),
            'max_concurrent': row.get('max_concurrent', 0)
        }
    
    # Add user details to display
    display_df['group'] = display_df['user_id'].map(lambda x: user_info.get(x, {}).get('group', 'N/A'))
    display_df['max_concurrent'] = display_df['user_id'].map(lambda x: user_info.get(x, {}).get('max_concurrent', 0))
    
    # Select columns to display
    columns_to_show = [
        'assignment_id', 'user_id', 'group', 'incident_short_desc', 
        'priority', 'assigned_at', 'max_concurrent'
    ]
    
    available_columns = [col for col in columns_to_show if col in display_df.columns]
    display_df = display_df[available_columns]
    
    # Display table with close buttons
    for idx, assignment in display_df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{assignment.get('incident_short_desc', 'N/A')[:50]}**")
                st.markdown(f"User: {assignment.get('user_id', 'N/A')} | Group: {assignment.get('group', 'N/A')}")
                st.markdown(f"Priority: {assignment.get('priority', 'N/A')} | Assigned: {assignment.get('assigned_at', 'N/A')}")
            
            with col2:
                # Show current workload vs max
                user_id = assignment.get('user_id', 'N/A')
                current_workload = workload_summary.get(user_id, 0)
                max_concurrent = assignment.get('max_concurrent', 0)
                
                st.markdown(f"**Workload:** {current_workload}/{max_concurrent}")
                
                # Color indicator
                if current_workload >= max_concurrent:
                    st.markdown("🔴 **At Capacity**")
                elif current_workload >= max_concurrent * 0.8:
                    st.markdown("🟡 **Near Capacity**")
                else:
                    st.markdown("🟢 **Available**")
            
            with col3:
                assignment_id = assignment.get('assignment_id', '')
                if st.button("🔒 Close Task", key=f"close_{assignment_id}"):
                    if storage.close_assignment(assignment_id):
                        st.success("✅ Task closed!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to close task")
            
            st.markdown("---")
    
    # Export functionality
    st.markdown("#### Export Options")
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        if st.button("📥 Export Open Assignments"):
            csv = open_assignments.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                f"open_assignments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv"
            )
    
    with col_exp2:
        if st.button("📊 Export Workload Summary"):
            workload_df = pd.DataFrame([
                {
                    'user_id': user_id,
                    'current_workload': count,
                    'max_concurrent': user_info.get(user_id, {}).get('max_concurrent', 0),
                    'group': user_info.get(user_id, {}).get('group', 'N/A'),
                    'capacity_utilization': f"{(count / user_info.get(user_id, {}).get('max_concurrent', 1)) * 100:.1f}%"
                }
                for user_id, count in workload_summary.items()
            ])
            
            csv = workload_df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                f"workload_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv"
            )

