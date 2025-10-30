"""Dashboard/home page"""
import streamlit as st
import pandas as pd
from datetime import datetime

def render(incidents_df, storage):
    st.title("🎫 Auto Ticket Assignment Dashboard")
    st.markdown("---")
    
    # Get statistics
    stats = storage.get_statistics()
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Assignments",
            stats['total_assignments'],
            delta=None
        )
    
    with col2:
        acceptance_rate = stats['acceptance_rate']
        st.metric(
            "Acceptance Rate",
            f"{acceptance_rate:.1f}%",
            delta=f"{acceptance_rate - 70:.1f}%",
            delta_color="normal" if acceptance_rate >= 70 else "inverse"
        )
        
        # Progress bar
        st.progress(min(acceptance_rate / 70, 1.0))
        st.caption("Goal: ≥70%")
    
    with col3:
        st.metric(
            "Time Saved",
            f"{stats['total_time_saved']:.0f} min",
            delta=f"~{stats['total_time_saved'] * 0.25:.0f} min faster",
            delta_color="off" if stats['total_time_saved'] == 0 else "normal"
        )
    
    with col4:
        st.metric(
            "Policy Violations",
            stats['policy_violations'],
            delta="0 target",
            delta_color="off"
        )
    
    st.markdown("---")
    
    # Key Performance Indicators
    st.markdown("### 📊 Key Performance Indicators")
    
    kpi_col1, kpi_col2 = st.columns(2)
    
    with kpi_col1:
        st.markdown("**Acceptance Rate Trend**")
        acceptance_rate = stats['acceptance_rate']
        
        if acceptance_rate >= 70:
            st.success(f"✅ Meeting goal: {acceptance_rate:.1f}% (Goal: ≥70%)")
        else:
            st.warning(f"⚠️ Below goal: {acceptance_rate:.1f}% (Goal: ≥70%)")
        
        # Visual progress
        st.progress(min(acceptance_rate / 100, 1.0))
    
    with kpi_col2:
        st.markdown("**Time-to-First-Response Improvement**")
        if stats['total_time_saved'] > 0:
            improvement = (stats['total_time_saved'] * 0.25) / stats['total_time_saved'] if stats['total_time_saved'] > 0 else 0
            st.success(f"✅ Estimated improvement: ~25% faster")
        else:
            st.info("⏳ Waiting for assignments")
    
    st.markdown("---")
    
    # Recent activity
    st.subheader("📋 Recent Incidents Available")
    if incidents_df is not None and len(incidents_df) > 0:
        # Get available columns (only those that exist)
        available_columns = []
        desired_columns = ['short_description', 'description', 'category', 'subcategory', 'priority', 'opened_at']
        
        for col in desired_columns:
            if col in incidents_df.columns:
                available_columns.append(col)
        
        if len(available_columns) > 0:
            display_df = incidents_df[available_columns].head(10)
            
            # Color code by priority only if priority column exists
            def color_priority(row):
                if 'priority' in row.index:
                    priority = row['priority']
                    color = {
                        'P1': '#ffebee',
                        'P2': '#fff3e0',
                        'P3': '#fffde7',
                        'P4': '#e8f5e9'
                    }.get(priority, '#ffffff')
                    return [f' странility: {color}' for _ in row]
                return ['' for _ in row]
            
            # Apply styling only if priority column exists
            if 'priority' in display_df.columns:
                st.dataframe(
                    display_df.style.apply(color_priority, axis=1),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
            
            st.caption(f"Showing {min(10, len(incidents_df))} of {len(incidents_df)} total incidents")
            
            # Show info about missing columns
            missing_cols = [col for col in desired_columns if col not in incidents_df.columns]
            if missing_cols:
                st.info(f"Note: Columns not found in data: {', '.join(missing_cols)}")
        else:
            st.dataframe(incidents_df.head(10), use_container_width=True, hide_index=True)
    else:
        st.info("No incidents available.")

