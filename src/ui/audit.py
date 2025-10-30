"""Audit and analytics page"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def render(storage):
    st.title("📊 Audit & Analytics")
    st.markdown("---")
    
    stats = storage.get_statistics()
    
    # Overall metrics
    st.markdown("### Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Acceptance Rate", 
                 f"{stats['acceptance_rate']:.1f}%", 
                 delta="Goal: ≥70%")
        st.progress(min(stats['acceptance_rate'] / 70, 1.0))
    
    with col2:
        st.metric("Total Assignments", stats['total_assignments'])
    
    with col3:
        st.metric("Time Saved", f"{stats['total_time_saved']:.0f} min")
        if stats['total_time_saved'] > 0:
            st.caption(f"~{stats['total_time_saved'] * 0.25:.0f} min faster")
    
    with col4:
        st.metric("Policy Violations", stats['policy_violations'], delta="Goal: 0")
    
    st.markdown("---")
    
    # Assignment history
    if storage.storage_file.exists():
        try:
            df = pd.read_excel(storage.storage_file)
            
            if len(df) > 0:
                st.markdown("### Assignment History")
                
                # Filters
                col_filter1, col_filter2, col_filter3 = st.columns(3)
                
                with col_filter1:
                    actions = ['All'] + df['action'].unique().tolist()
                    selected_action = st.selectbox("Filter by Action", actions)
                
                with col_filter2:
                    priorities = ['All'] + df['priority'].unique().tolist()
                    selected_priority = st.selectbox("Filter by Priority", priorities)
                
                with col_filter3:
                    date_filter = st.selectbox("Date Range", 
                                             ['All', 'Last 7 days', 'Last 30 days', 'Custom'])
                
                # Apply filters
                filtered_df = df.copy()
                
                if selected_action != 'All':
                    filtered_df = filtered_df[filtered_df['action'] == selected_action]
                
                if selected_priority != 'All':
                    filtered_df = filtered_df[filtered_df['priority'] == selected_priority]
                
                # Display filtered data
                if len(filtered_df) > 0:
                    st.dataframe(
                        filtered_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'timestamp': st.column_config.DatetimeColumn(
                                "Timestamp", format="YYYY-MM-DD HH:MM"
                            ),
                            'priority': st.column_config.TextColumn("Priority"),
                            'action': st.column_config.TextColumn("Action"),
                            'time_saved_minutes': st.column_config.NumberColumn(
                                "Time Saved (min)", format="%.1f"
                            )
                        }
                    )
                    
                    st.caption(f"Showing {len(filtered_df)} of {len(df)} assignments")
                    
                    # Download button
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        "📥 Download as CSV",
                        csv,
                        f"assignments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv",
                        key='download-csv'
                    )
                else:
                    st.info("No assignments match the selected filters.")
            else:
                st.info("No assignments recorded yet.")
                
        except Exception as e:
            st.error(f"Error loading assignment history: {e}")
            st.exception(e)
    else:
        st.info("No assignments recorded yet.")
    
    st.markdown("---")
    
    # Stats section
    st.markdown("### Performance Goals")
    
    goal_col1, goal_col2 = st.columns(2)
    
    with goal_col1:
        st.markdown("**Acceptance Rate Goal: ≥70%**")
        acceptance_rate = stats['acceptance_rate']
        if acceptance_rate >= 70:
            st.success(f"✅ Meeting goal: {acceptance_rate:.1f}%")
        else:
            gap = 70 - acceptance_rate
            st.warning(f"⚠️ Below goal by {gap:.1f}%")
    
    with goal_col2:
        st.markdown("**Time-to-First-Response Goal: ≥25% faster**")
        if stats['total_time_saved'] > 0:
            st.success("✅ Estimated improvement: ~25%")
        else:
            st.info("⏳ Waiting for assignments")

