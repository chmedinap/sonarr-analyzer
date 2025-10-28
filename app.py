"""
Sonarr Series Size Analyzer - Extended Version with Historical Tracking
Analyzes average file size per episode for TV series managed by Sonarr.
Includes encrypted credential storage and historical data comparison.
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any, Tuple, Optional
import json
import time
from datetime import datetime, timedelta
import io
from pathlib import Path

# Import custom modules
from security import CredentialManager
from storage import HistoryDatabase

# Page configuration
st.set_page_config(
    page_title="Sonarr Size Analyzer - Extended",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
DEFAULT_TIMEOUT = 10
DEFAULT_Z_THRESHOLD = 2.0
MAX_RETRIES = 2
MAX_RESPONSE_SIZE = 200 * 1024 * 1024  # 200 MB
DB_PATH = "data/sonarr_history.db"
CREDENTIALS_FILE = "data/.sonarr_credentials.enc"

# Ensure data directory exists
Path("data").mkdir(exist_ok=True)

# Initialize managers
if 'credential_manager' not in st.session_state:
    st.session_state.credential_manager = CredentialManager(CREDENTIALS_FILE)

if 'history_db' not in st.session_state:
    st.session_state.history_db = HistoryDatabase(DB_PATH)

# Custom CSS
st.markdown("""
<style>
    .reportview-container .main .block-container {
        padding-top: 2rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
    }
    .metric-positive {
        color: #28a745;
    }
    .metric-negative {
        color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)


def validate_url(url: str) -> Tuple[bool, str, str]:
    """Validate and sanitize base URL."""
    if not url:
        return False, "", "URL cannot be empty"
    
    url = url.strip().rstrip('/')
    
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
        st.warning("⚠️ No scheme provided, defaulting to HTTP. Consider using HTTPS for security.")
    
    if not url.startswith(('http://', 'https://')):
        return False, "", "Only HTTP and HTTPS schemes are allowed"
    
    return True, url, ""


def fetch_sonarr_data(
    endpoint: str,
    base_url: str,
    api_key: str,
    timeout: int = DEFAULT_TIMEOUT,
    params: Optional[Dict] = None
) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """Fetch data from Sonarr API endpoint with error handling."""
    url = f"{base_url}/{endpoint}"
    headers = {"X-Api-Key": api_key}
    
    session = requests.Session()
    session.headers.update(headers)
    
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(
                url,
                timeout=timeout,
                params=params,
                stream=False
            )
            
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > MAX_RESPONSE_SIZE:
                return None, f"Response too large: {int(content_length) / (1024**2):.1f} MB"
            
            if response.status_code == 401:
                return None, "❌ Authentication failed: Invalid API key"
            elif response.status_code == 403:
                return None, "❌ Access forbidden: Check API key permissions"
            elif response.status_code == 404:
                return None, "❌ Endpoint not found: Check Sonarr URL and version"
            elif response.status_code >= 500:
                return None, f"❌ Sonarr server error: {response.status_code}"
            
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, list):
                return None, f"Unexpected response format: expected list, got {type(data).__name__}"
            
            return data, None
            
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                time.sleep(1)
                continue
            return None, f"⏱️ Request timeout after {timeout}s"
            
        except requests.exceptions.ConnectionError:
            return None, "🔌 Connection failed: Check URL and network connectivity"
            
        except requests.exceptions.RequestException as e:
            return None, f"❌ Request error: {str(e)}"
            
        except json.JSONDecodeError:
            return None, "❌ Invalid JSON response from Sonarr"
    
    return None, "Failed after multiple retries"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_episode_files(
    series_data: List[Dict],
    base_url: str,
    api_key: str,
    timeout: int
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Fetch episode files for all series with progress tracking."""
    all_episode_files = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_series = len(series_data)
    
    for idx, series in enumerate(series_data):
        series_id = series.get('id')
        series_title = series.get('title', 'Unknown')
        
        if series_id is None:
            continue
        
        progress = (idx + 1) / total_series
        progress_bar.progress(progress)
        status_text.text(f"Processing {idx + 1}/{total_series}: {series_title}")
        
        endpoint = f"api/v3/episodefile"
        params = {"seriesId": series_id}
        
        episode_files, error = fetch_sonarr_data(
            endpoint, base_url, api_key, timeout, params
        )
        
        if error:
            continue
        
        if episode_files:
            for ef in episode_files:
                all_episode_files.append({
                    'episode_file_id': ef.get('id'),
                    'series_id': ef.get('seriesId'),
                    'size_bytes': ef.get('size', 0),
                    'quality': ef.get('quality', {}).get('quality', {}).get('name', 'Unknown')
                })
    
    progress_bar.empty()
    status_text.empty()
    
    if not all_episode_files:
        return None, "No episode files found in any series"
    
    return pd.DataFrame(all_episode_files), None


def compute_metrics(
    series_df: pd.DataFrame,
    episodefile_df: pd.DataFrame
) -> pd.DataFrame:
    """Compute size metrics for each series."""
    series_stats = episodefile_df.groupby('series_id').agg(
        episode_count=('episode_file_id', 'count'),
        total_size_bytes=('size_bytes', 'sum')
    ).reset_index()
    
    series_stats['total_size_gb'] = series_stats['total_size_bytes'] / (1024**3)
    series_stats['avg_size_mb'] = (
        series_stats['total_size_bytes'] / series_stats['episode_count']
    ) / (1024**2)
    
    analysis_df = series_df.merge(series_stats, on='series_id', how='left')
    
    analysis_df['episode_count'] = analysis_df['episode_count'].fillna(0).astype(int)
    analysis_df['total_size_gb'] = analysis_df['total_size_gb'].fillna(0)
    analysis_df['avg_size_mb'] = analysis_df['avg_size_mb'].fillna(0)
    
    analysis_df = analysis_df[analysis_df['episode_count'] > 0].copy()
    
    return analysis_df


def detect_outliers(
    df: pd.DataFrame,
    z_threshold: float = 2.0,
    absolute_threshold: Optional[float] = None
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Detect outliers based on Z-score and optional absolute threshold."""
    if len(df) == 0:
        return df, {}
    
    mean_size = df['avg_size_mb'].mean()
    std_size = df['avg_size_mb'].std()
    
    df['z_score'] = (df['avg_size_mb'] - mean_size) / std_size if std_size > 0 else 0
    
    z_outlier_threshold = mean_size + z_threshold * std_size
    df['is_outlier'] = df['avg_size_mb'] > z_outlier_threshold
    
    if absolute_threshold is not None:
        df['is_outlier'] = df['is_outlier'] | (df['avg_size_mb'] > absolute_threshold)
    
    stats = {
        'mean': mean_size,
        'std': std_size,
        'z_threshold': z_outlier_threshold,
        'outlier_count': int(df['is_outlier'].sum()),
        'outlier_percentage': (df['is_outlier'].sum() / len(df) * 100) if len(df) > 0 else 0
    }
    
    return df, stats


# ============================================================================
# CONFIGURATION PAGE
# ============================================================================

def show_configuration_page():
    """Display configuration page for credentials and settings."""
    st.title("⚙️ Configuration")
    
    st.markdown("### Sonarr Connection")
    
    cred_manager = st.session_state.credential_manager
    
    # Check if credentials exist
    creds_exist = cred_manager.credentials_exist()
    
    if creds_exist:
        st.success("✅ Encrypted credentials found")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔓 Load Saved Credentials", type="primary"):
                st.session_state.show_load_creds = True
        
        with col2:
            if st.button("🗑️ Delete Saved Credentials", type="secondary"):
                success, msg = cred_manager.delete_credentials()
                if success:
                    st.success(msg)
                    st.session_state.base_url = ""
                    st.session_state.api_key = ""
                    st.rerun()
                else:
                    st.error(msg)
        
        if st.session_state.get('show_load_creds', False):
            st.markdown("---")
            st.markdown("#### Load Encrypted Credentials")
            
            passphrase = st.text_input(
                "Enter passphrase to decrypt",
                type="password",
                key="load_passphrase"
            )
            
            if st.button("Load"):
                if passphrase:
                    success, creds, msg = cred_manager.load_credentials(passphrase)
                    
                    if success:
                        st.session_state.base_url = creds['base_url']
                        st.session_state.api_key = creds['api_key']
                        st.session_state.show_load_creds = False
                        st.success("✅ Credentials loaded successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please enter passphrase")
    
    st.markdown("---")
    st.markdown("### Manual Configuration")
    
    # Manual inputs
    base_url = st.text_input(
        "Sonarr URL",
        value=st.session_state.get('base_url', ''),
        placeholder="http://localhost:8989",
        help="URL where your Sonarr instance is accessible",
        key="config_base_url"
    )
    
    api_key = st.text_input(
        "API Key",
        value=st.session_state.get('api_key', ''),
        type="password",
        placeholder="Your API key",
        help="Found in Sonarr → Settings → General → Security",
        key="config_api_key"
    )
    
    # Save credentials option
    st.markdown("---")
    st.markdown("### Save Credentials (Encrypted)")
    
    st.warning("""
    ⚠️ **Security Information:**
    - Credentials will be encrypted with AES-256 using your passphrase
    - You must remember your passphrase (cannot be recovered)
    - Passphrase should be at least 8 characters
    - Files stored: `.sonarr_credentials.enc`, `.sonarr_salt`
    """)
    
    save_creds = st.checkbox(
        "I want to save these credentials encrypted",
        value=False
    )
    
    if save_creds and base_url and api_key:
        passphrase = st.text_input(
            "Create a strong passphrase (min 8 characters)",
            type="password",
            help="This passphrase will be required to decrypt your credentials",
            key="save_passphrase"
        )
        
        passphrase_confirm = st.text_input(
            "Confirm passphrase",
            type="password",
            key="save_passphrase_confirm"
        )
        
        if st.button("💾 Save Encrypted Credentials", type="primary"):
            if len(passphrase) < 8:
                st.error("Passphrase must be at least 8 characters")
            elif passphrase != passphrase_confirm:
                st.error("Passphrases don't match")
            else:
                success, msg = cred_manager.save_credentials(
                    base_url,
                    api_key,
                    passphrase
                )
                
                if success:
                    st.success(msg)
                    st.session_state.base_url = base_url
                    st.session_state.api_key = api_key
                    st.balloons()
                else:
                    st.error(msg)
    
    elif save_creds:
        st.info("Please enter both URL and API key above to save")
    
    # Apply button for manual config
    if not save_creds:
        if st.button("Apply Configuration", type="primary"):
            if base_url and api_key:
                st.session_state.base_url = base_url
                st.session_state.api_key = api_key
                st.success("✅ Configuration applied!")
            else:
                st.warning("Please enter both URL and API key")


# ============================================================================
# ANALYSIS PAGE (Original functionality)
# ============================================================================

def show_analysis_page():
    """Display current analysis page."""
    st.title("📊 Current Analysis")
    
    # Check if credentials are configured
    base_url = st.session_state.get('base_url', '')
    api_key = st.session_state.get('api_key', '')
    
    if not base_url or not api_key:
        st.warning("⚠️ Please configure your Sonarr credentials in the Configuration page")
        st.info("Go to **⚙️ Configuration** in the sidebar to set up your connection")
        return
    
    # Show current configuration
    with st.expander("🔧 Current Configuration"):
        st.write(f"**Sonarr URL:** {base_url}")
        st.write(f"**API Key:** {'*' * 20}{api_key[-4:]}")
    
    # Advanced options
    with st.expander("🔧 Advanced Options"):
        timeout = st.number_input(
            "Request Timeout (seconds)",
            min_value=5,
            max_value=60,
            value=DEFAULT_TIMEOUT
        )
        
        z_threshold = st.number_input(
            "Z-Score Threshold",
            min_value=1.0,
            max_value=5.0,
            value=DEFAULT_Z_THRESHOLD,
            step=0.5
        )
        
        absolute_threshold = st.number_input(
            "Absolute Threshold (MB/episode)",
            min_value=0,
            max_value=10000,
            value=0
        )
        
        if absolute_threshold == 0:
            absolute_threshold = None
        
        save_to_history = st.checkbox(
            "💾 Save this analysis to history",
            value=True,
            help="Store results for future comparison"
        )
    
    # Analyze button
    if st.button("🚀 Run Analysis", type="primary"):
        is_valid, base_url, error = validate_url(base_url)
        if not is_valid:
            st.error(f"❌ Invalid URL: {error}")
            return
        
        try:
            with st.spinner("🔄 Connecting to Sonarr..."):
                # Fetch series
                series_data, error = fetch_sonarr_data(
                    "api/v3/series",
                    base_url,
                    api_key,
                    timeout
                )
                
                if error:
                    st.error(error)
                    return
                
                if not series_data:
                    st.error("No series found in Sonarr")
                    return
                
                st.success(f"✅ Found {len(series_data)} series")
                
                # Fetch episode files
                series_df = pd.DataFrame([
                    {
                        'series_id': s.get('id'),
                        'title': s.get('title', 'Unknown'),
                        'year': s.get('year', 'N/A'),
                        'status': s.get('status', 'Unknown')
                    }
                    for s in series_data
                ])
                
                episodefile_df, error = fetch_all_episode_files(
                    series_data,
                    base_url,
                    api_key,
                    timeout
                )
                
                if error:
                    st.error(error)
                    return
                
                st.success(f"✅ Found {len(episodefile_df)} episode files")
            
            # Compute metrics
            with st.spinner("📊 Computing metrics..."):
                analysis_df = compute_metrics(series_df, episodefile_df)
                
                if len(analysis_df) == 0:
                    st.warning("No series with episode files found")
                    return
                
                analysis_df, stats = detect_outliers(
                    analysis_df,
                    z_threshold,
                    absolute_threshold
                )
            
            # Save to history if requested
            if save_to_history:
                success, msg = st.session_state.history_db.save_analysis(
                    analysis_df,
                    stats,
                    overwrite=True
                )
                
                if success:
                    st.success(f"💾 {msg}")
                else:
                    st.warning(f"⚠️ {msg}")
            
            # Store in session state
            st.session_state['analysis_df'] = analysis_df
            st.session_state['stats'] = stats
            st.session_state['analysis_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            st.success("✅ Analysis complete!")
            
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            st.exception(e)
    
    # Display results if available
    if 'analysis_df' in st.session_state and st.session_state['analysis_df'] is not None:
        analysis_df = st.session_state['analysis_df']
        stats = st.session_state['stats']
        
        st.markdown("---")
        
        # Summary metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Series", len(analysis_df))
        
        with col2:
            total_episodes = int(analysis_df['episode_count'].sum())
            st.metric("Total Episodes", f"{total_episodes:,}")
        
        with col3:
            total_size = analysis_df['total_size_gb'].sum()
            st.metric("Total Storage", f"{total_size:.1f} GB")
        
        with col4:
            st.metric("Avg Size/Episode", f"{stats.get('mean', 0):.0f} MB")
        
        with col5:
            outlier_count = stats.get('outlier_count', 0)
            outlier_pct = stats.get('outlier_percentage', 0)
            st.metric(
                "Outliers",
                outlier_count,
                f"{outlier_pct:.1f}%",
                delta_color="inverse"
            )
        
        # Visualizations tabs
        tab1, tab2, tab3 = st.tabs(["📋 Table", "📊 Charts", "🚨 Outliers"])
        
        with tab1:
            st.subheader("Series Analysis Table")
            display_df = analysis_df[[
                'title', 'episode_count', 'total_size_gb', 'avg_size_mb', 'z_score', 'is_outlier'
            ]].copy()
            
            display_df.columns = [
                'Series Title', 'Episodes', 'Total Size (GB)',
                'Avg Size (MB)', 'Z-Score', 'Outlier'
            ]
            
            display_df = display_df.sort_values('Avg Size (MB)', ascending=False)
            st.dataframe(display_df, use_container_width=True, height=400)
        
        with tab2:
            # Bar chart
            st.subheader("Top 20 Series by Average Size")
            top_20 = analysis_df.nlargest(20, 'avg_size_mb')
            colors = ['#e74c3c' if outlier else '#3498db' for outlier in top_20['is_outlier']]
            
            fig = go.Figure(go.Bar(
                y=top_20['title'],
                x=top_20['avg_size_mb'],
                orientation='h',
                marker=dict(color=colors),
                text=top_20['avg_size_mb'].round(1),
                textposition='outside'
            ))
            
            fig.update_layout(
                xaxis_title="Average Size per Episode (MB)",
                height=600,
                yaxis={'categoryorder': 'total ascending'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.subheader("Outlier Series")
            outliers = analysis_df[analysis_df['is_outlier'] == True]
            
            if len(outliers) > 0:
                st.warning(f"Found {len(outliers)} series with unusually high file sizes")
                
                for idx, (i, row) in enumerate(outliers.head(10).iterrows(), 1):
                    with st.expander(f"#{idx} - {row['title']} ({row['avg_size_mb']:.0f} MB/episode)"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Episodes:** {row['episode_count']}")
                            st.write(f"**Total Size:** {row['total_size_gb']:.2f} GB")
                        
                        with col2:
                            st.write(f"**Avg Size:** {row['avg_size_mb']:.1f} MB")
                            st.write(f"**Z-Score:** {row['z_score']:.2f}")
            else:
                st.success("✅ No outliers detected!")


# ============================================================================
# HISTORICAL ANALYSIS PAGE
# ============================================================================

def show_history_page():
    """Display historical analysis and comparison page."""
    st.title("📈 Historical Analysis")
    
    db = st.session_state.history_db
    
    # Get available dates
    available_dates = db.get_analysis_dates()
    
    if not available_dates:
        st.info("📭 No historical data available yet. Run an analysis first!")
        return
    
    st.success(f"📊 Found {len(available_dates)} historical analyses")
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs([
        "📅 All Analyses",
        "🔄 Compare Dates",
        "📈 Trends",
        "⚙️ Manage Data"
    ])
    
    # ========== TAB 1: All Analyses ==========
    with tab1:
        st.subheader("All Historical Analyses")
        
        # Load global trends
        trends_df = db.get_global_trends()
        
        if trends_df is not None and len(trends_df) > 0:
            st.dataframe(
                trends_df[[
                    'analysis_date', 'total_series', 'total_episodes',
                    'total_storage_gb', 'mean_avg_size_mb', 'outlier_count'
                ]],
                use_container_width=True
            )
            
            # Storage evolution chart
            st.subheader("Storage Evolution Over Time")
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trends_df['analysis_date'],
                y=trends_df['total_storage_gb'],
                mode='lines+markers',
                name='Total Storage (GB)',
                line=dict(color='#3498db', width=3)
            ))
            
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Total Storage (GB)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Average size evolution
            st.subheader("Average Episode Size Evolution")
            
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=trends_df['analysis_date'],
                y=trends_df['mean_avg_size_mb'],
                mode='lines+markers',
                name='Mean Avg Size (MB)',
                line=dict(color='#2ecc71', width=3)
            ))
            
            fig2.update_layout(
                xaxis_title="Date",
                yaxis_title="Mean Average Size (MB)",
                height=400
            )
            
            st.plotly_chart(fig2, use_container_width=True)
    
    # ========== TAB 2: Compare Dates ==========
    with tab2:
        st.subheader("Compare Two Analyses")
        
        col1, col2 = st.columns(2)
        
        with col1:
            date1 = st.selectbox(
                "Select first date (older)",
                options=available_dates,
                index=min(1, len(available_dates)-1) if len(available_dates) > 1 else 0,
                key="compare_date1"
            )
        
        with col2:
            date2 = st.selectbox(
                "Select second date (newer)",
                options=available_dates,
                index=0,
                key="compare_date2"
            )
        
        if st.button("🔄 Compare", type="primary"):
            if date1 == date2:
                st.warning("Please select two different dates")
            else:
                with st.spinner("Comparing analyses..."):
                    comparison_df = db.compare_dates(date1, date2)
                    
                    if comparison_df is None or len(comparison_df) == 0:
                        st.error("Failed to compare dates")
                    else:
                        # Summary metrics
                        st.subheader("Comparison Summary")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        new_series = len(comparison_df[comparison_df['status'] == 'new'])
                        removed_series = len(comparison_df[comparison_df['status'] == 'removed'])
                        total_change = comparison_df['size_change_gb'].sum()
                        
                        with col1:
                            st.metric("New Series", new_series)
                        
                        with col2:
                            st.metric("Removed Series", removed_series)
                        
                        with col3:
                            st.metric(
                                "Storage Change",
                                f"{abs(total_change):.1f} GB",
                                delta=f"{total_change:+.1f} GB",
                                delta_color="inverse" if total_change < 0 else "normal"
                            )
                        
                        with col4:
                            avg_change = comparison_df[comparison_df['status'] == 'existing']['avg_size_change_mb'].mean()
                            st.metric(
                                "Avg Size Change",
                                f"{abs(avg_change):.0f} MB",
                                delta=f"{avg_change:+.0f} MB"
                            )
                        
                        # Detailed comparison table
                        st.subheader("Detailed Comparison")
                        
                        # Format display
                        display_comp = comparison_df.copy()
                        display_comp['episode_count_old'] = display_comp['episode_count_old'].fillna(0).astype(int)
                        display_comp['episode_count_new'] = display_comp['episode_count_new'].fillna(0).astype(int)
                        
                        st.dataframe(
                            display_comp[[
                                'series_title', 'status', 'episodes_change',
                                'size_change_gb', 'size_change_pct', 'avg_size_change_mb'
                            ]],
                            use_container_width=True,
                            height=400
                        )
                        
                        # Top changers chart
                        st.subheader("Top 10 Size Changes")
                        
                        top_changes = comparison_df.nlargest(10, 'abs_size_change') if 'abs_size_change' in comparison_df else comparison_df.head(10)
                        
                        fig = go.Figure()
                        
                        colors = ['#28a745' if x < 0 else '#dc3545' for x in top_changes['size_change_gb']]
                        
                        fig.add_trace(go.Bar(
                            y=top_changes['series_title'],
                            x=top_changes['size_change_gb'],
                            orientation='h',
                            marker=dict(color=colors),
                            text=top_changes['size_change_gb'].round(2),
                            textposition='outside'
                        ))
                        
                        fig.update_layout(
                            xaxis_title="Size Change (GB)",
                            yaxis_title="",
                            height=500,
                            yaxis={'categoryorder': 'total ascending'}
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Export comparison
                        csv_data = comparison_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Comparison CSV",
                            data=csv_data,
                            file_name=f"comparison_{date1[:10]}_vs_{date2[:10]}.csv",
                            mime="text/csv"
                        )
    
    # ========== TAB 3: Trends ==========
    with tab3:
        st.subheader("Series Trends Over Time")
        
        # Select a specific series to track
        # First, get a list of all series that appear in history
        conn = db.db_path
        import sqlite3
        conn_obj = sqlite3.connect(conn)
        series_list = pd.read_sql_query("""
            SELECT DISTINCT series_id, series_title 
            FROM history 
            ORDER BY series_title
        """, conn_obj)
        conn_obj.close()
        
        if len(series_list) > 0:
            selected_series = st.selectbox(
                "Select series to track",
                options=series_list['series_id'].tolist(),
                format_func=lambda x: series_list[series_list['series_id'] == x]['series_title'].iloc[0]
            )
            
            if st.button("📊 Show Trend"):
                # Get time series for this series
                ts_size = db.get_time_series(selected_series, 'total_size_gb')
                ts_episodes = db.get_time_series(selected_series, 'episode_count')
                ts_avg = db.get_time_series(selected_series, 'avg_size_mb')
                
                if ts_size is not None and len(ts_size) > 0:
                    series_name = ts_size['series_title'].iloc[0]
                    
                    st.subheader(f"Trend for: {series_name}")
                    
                    # Create multi-axis chart
                    from plotly.subplots import make_subplots
                    
                    fig = make_subplots(
                        rows=3, cols=1,
                        subplot_titles=("Total Size (GB)", "Episode Count", "Average Size (MB)"),
                        vertical_spacing=0.1
                    )
                    
                    fig.add_trace(
                        go.Scatter(x=ts_size['analysis_date'], y=ts_size['total_size_gb'],
                                 mode='lines+markers', name='Total Size'),
                        row=1, col=1
                    )
                    
                    fig.add_trace(
                        go.Scatter(x=ts_episodes['analysis_date'], y=ts_episodes['episode_count'],
                                 mode='lines+markers', name='Episodes'),
                        row=2, col=1
                    )
                    
                    fig.add_trace(
                        go.Scatter(x=ts_avg['analysis_date'], y=ts_avg['avg_size_mb'],
                                 mode='lines+markers', name='Avg Size'),
                        row=3, col=1
                    )
                    
                    fig.update_layout(height=900, showlegend=False)
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No historical data for this series")
        else:
            st.info("No series data in history yet")
    
    # ========== TAB 4: Manage Data ==========
    with tab4:
        st.subheader("Manage Historical Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Delete Specific Analysis")
            
            date_to_delete = st.selectbox(
                "Select date to delete",
                options=available_dates,
                key="delete_date"
            )
            
            if st.button("🗑️ Delete Analysis", type="secondary"):
                if st.session_state.get('confirm_delete', False):
                    success, msg = db.delete_analysis(date_to_delete)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                    st.session_state.confirm_delete = False
                else:
                    st.session_state.confirm_delete = True
                    st.warning("Click again to confirm deletion")
        
        with col2:
            st.markdown("#### Cleanup Old Data")
            
            days_to_keep = st.number_input(
                "Keep data from last N days",
                min_value=7,
                max_value=365,
                value=90
            )
            
            if st.button("🧹 Cleanup Old Data"):
                success, msg = db.cleanup_old_data(days_to_keep)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        
        st.markdown("---")
        st.markdown("#### Export All Historical Data")
        
        if st.button("📥 Export History to CSV"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"sonarr_history_export_{timestamp}.csv"
            
            success, msg = db.export_to_csv(output_path)
            
            if success:
                st.success(msg)
                
                with open(output_path, 'rb') as f:
                    st.download_button(
                        label="Download Export",
                        data=f,
                        file_name=output_path,
                        mime="text/csv"
                    )
            else:
                st.error(msg)


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point."""
    
    # Sidebar navigation
    with st.sidebar:
        st.title("📊 Sonarr Analyzer")
        st.markdown("Extended Edition")
        
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            options=["🔍 Current Analysis", "📈 Historical Data", "⚙️ Configuration"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Quick stats if available
        if st.session_state.get('analysis_df') is not None:
            st.markdown("### Last Analysis")
            df = st.session_state['analysis_df']
            st.metric("Series", len(df))
            st.metric("Storage", f"{df['total_size_gb'].sum():.0f} GB")
        
        # Database info
        db = st.session_state.history_db
        dates = db.get_analysis_dates()
        if dates:
            st.markdown("---")
            st.markdown("### Historical Data")
            st.metric("Analyses Saved", len(dates))
            st.caption(f"Latest: {dates[0][:10]}")
    
    # Route to appropriate page
    if "Current Analysis" in page:
        show_analysis_page()
    elif "Historical" in page:
        show_history_page()
    elif "Configuration" in page:
        show_configuration_page()


if __name__ == "__main__":
    main()

