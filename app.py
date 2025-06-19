import streamlit as st
import pandas as pd
import requests
import re
import json
import time
import io
from typing import Tuple, Optional, List, Dict, Any
import logging

# ========================================
# CONFIGURATION & CONSTANTS
# ========================================

# Page configuration
PAGE_CONFIG = {
    "page_title": "Email Verifier Pro",
    "page_icon": "📧",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# API Configuration
API_CONFIG = {
    "base_url": "https://emailverifier.reoon.com/api/v1/verify",
    "timeout": 30,
    "delay_between_requests": 0.3
}

# Email validation
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Required field mapping
REQUIRED_FIELDS = {
    'firstname': 'First Name',
    'lastname': 'Last Name', 
    'companyURL': 'Company URL'
}

# Status mappings
FORBIDDEN_EMAIL_STATUSES = ["invalid", "disabled", "unknown"]

# ========================================
# LOGGING SETUP
# ========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========================================
# CUSTOM CSS STYLES
# ========================================

def load_custom_css():
    """Load custom CSS for beautiful UI."""
    st.markdown("""
    <style>
        .main-header {
            font-size: 3rem;
            font-weight: bold;
            text-align: center;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 2rem;
        }
        
        .sub-header {
            text-align: center;
            color: #666;
            font-size: 1.2rem;
            margin-bottom: 3rem;
        }
        
        .stButton > button {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.5rem 2rem;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .stats-card {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .success-text {
            color: #28a745;
            font-weight: bold;
        }
        
        .error-text {
            color: #dc3545;
            font-weight: bold;
        }
        
        .info-text {
            color: #17a2b8;
            font-weight: bold;
        }
        
        .result-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            margin: 1rem 0;
        }
        
        .result-card h3 {
            margin: 0 0 1rem 0;
            font-size: 1.5rem;
        }
        
        .result-card p {
            margin: 0.5rem 0;
            font-size: 1.1rem;
        }
        
        .email-found {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 10px;
            text-align: center;
            margin: 1rem 0;
            font-size: 1.2rem;
            font-weight: bold;
        }
        
        .email-not-found {
            background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 10px;
            text-align: center;
            margin: 1rem 0;
            font-size: 1.2rem;
            font-weight: bold;
        }
        
        .efficiency-card {
            background: linear-gradient(135deg, #17a2b8 0%, #20c997 100%);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
        }
        
        /* Dialog specific styles */
        .stDialog > div {
            background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%);
        }
        
        .stDialog h3 {
            color: #667eea;
            font-weight: bold;
        }
        
        .api-welcome {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)

# ========================================
# INPUT VALIDATION FUNCTIONS
# ========================================

def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False
    return bool(re.match(EMAIL_REGEX, email.strip()))

def validate_api_key(api_key: str) -> bool:
    """Validate API key format."""
    if not api_key or not isinstance(api_key, str):
        return False
    return len(api_key.strip()) > 10

def validate_column_mapping(column_mapping: Dict[str, str], df_columns: List[str]) -> Tuple[bool, List[str]]:
    """Validate that all required fields are mapped to valid columns."""
    errors = []
    
    for field, display_name in REQUIRED_FIELDS.items():
        if field not in column_mapping or not column_mapping[field]:
            errors.append(f"{display_name} is not mapped")
        elif column_mapping[field] not in df_columns:
            errors.append(f"{display_name} is mapped to non-existent column")
    
    # Check for duplicate mappings
    mapped_columns = [col for col in column_mapping.values() if col]
    if len(mapped_columns) != len(set(mapped_columns)):
        errors.append("Cannot map multiple fields to the same column")
    
    return len(errors) == 0, errors

# ========================================
# CORE EMAIL VERIFICATION FUNCTIONS
# ========================================

class EmailVerifier:
    """Core email verification functionality."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        
    def clean_domain(self, domain_raw: str) -> str:
        """Clean and normalize domain name."""
        if not isinstance(domain_raw, str) or not domain_raw.strip():
            return ""
        
        domain = re.sub(r'^https?://', '', domain_raw.strip(), flags=re.IGNORECASE)
        domain = re.sub(r'^www\.', '', domain, flags=re.IGNORECASE)
        domain = domain.split('/')[0]
        return domain.strip().lower()
    
    def parse_name(self, full_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Parse full name into first, middle, last components."""
        if not isinstance(full_name, str) or not full_name.strip():
            return None, None, None
        
        parts = full_name.strip().split()
        first_name = ''
        middle_name = None
        last_name = ''

        if len(parts) >= 1: 
            first_name = parts[0].lower()
        if len(parts) == 2: 
            last_name = parts[1].lower()
        elif len(parts) >= 3:
            middle_name = " ".join(parts[1:-1]).lower()
            last_name = parts[-1].lower()

        # Clean names
        first_name = re.sub(r'[^a-z]', '', first_name)
        last_name = re.sub(r'[^a-z]', '', last_name)
        if middle_name: 
            middle_name = re.sub(r'[^a-z]', '', middle_name)

        if len(parts) == 1 and first_name: 
            last_name = first_name
        if not first_name and not last_name: 
            return None, None, None

        return first_name, middle_name, last_name
    
    def generate_email_formats(self, first_name: str, middle_name: Optional[str], last_name: str, domain: str) -> List[str]:
        """Generate potential email formats based on name components."""
        potential_locals = []
        f = first_name[0] if first_name else ''
        m = middle_name[0] if middle_name else ''
        l = last_name[0] if last_name else ''

        # Generate various email format patterns
        patterns = [
            f"{f}{last_name}",  # jdoe
            f"{first_name}",  # john
            f"{first_name}.{last_name}",  # john.doe
            f"{last_name}",  # doe
            f"{f}{l}",  # jd
            f"{first_name}{last_name}",  # johndoe
            f"{first_name}{l}",  # johnd
            f"{last_name}{f}",  # doej
            f"{last_name}.{f}",  # doe.j
            f"{last_name}{first_name}",  # doejohn
            f"{first_name}_{last_name}",  # john_doe
        ]
        
        # Add middle name patterns if available
        if middle_name:
            patterns.extend([
                f"{f}{m}{l}",  # jml
                f"{first_name}.{m}.{last_name}",  # john.m.doe
                f"{f}{m}{last_name}",  # jmdoe
            ])

        # Filter and deduplicate
        potential_locals = [pattern for pattern in patterns if pattern and len(pattern) > 0]
        generated_emails = list(dict.fromkeys([f"{local_part}@{domain}" for local_part in potential_locals]))
        
        return generated_emails
    
    def verify_email_api(self, email: str) -> Dict[str, Any]:
        """Call the Reoon Email Verifier API."""
        api_url = f"{API_CONFIG['base_url']}?email={email}&key={self.api_key}&mode=power"
        
        try:
            response = self.session.get(api_url, timeout=API_CONFIG['timeout'])
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {email}: {e}")
            return {"error": f"API Request Failed: {e}"}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode API response for {email}: {e}")
            return {"error": "Failed to decode API response"}
    
    def verify_single_email(self, firstname: str, lastname: str, company_url: str) -> Optional[Dict[str, Any]]:
        """Verify email for a single person, stopping when valid email is found."""
        # Clean and parse inputs
        domain = self.clean_domain(company_url)
        if not domain:
            return None
        
        # Combine names
        full_name = f"{firstname} {lastname}".strip()
        first, middle, last = self.parse_name(full_name)
        
        if not first or not last:
            return None
        
        # Generate email formats
        email_formats = self.generate_email_formats(first, middle, last, domain)
        
        # Track testing progress
        formats_tested = []
        
        # Test each format until we find a valid one
        for i, email in enumerate(email_formats):
            formats_tested.append(email)
            
            try:
                result = self.verify_email_api(email)
                
                if result and 'error' not in result:
                    status = result.get("status", "unknown")
                    
                    # If status is valid (not in forbidden list), return immediately
                    if status not in FORBIDDEN_EMAIL_STATUSES:
                        return {
                            'firstname': firstname,
                            'lastname': lastname,
                            'company': domain,
                            'email': email,
                            'status': status,
                            'full_name': full_name,
                            'formats_tested': formats_tested,
                            'total_formats_available': len(email_formats),
                            'found_on_attempt': len(formats_tested),
                            'api_result': result
                        }
                
                # Add delay between requests to avoid rate limiting
                if i < len(email_formats) - 1:
                    time.sleep(API_CONFIG['delay_between_requests'])
                    
            except Exception as e:
                logger.error(f"API error for {email}: {str(e)}")
                continue
        
        # No valid email found after testing all formats
        return {
            'firstname': firstname,
            'lastname': lastname,
            'company': domain,
            'email': None,
            'status': 'not_found',
            'full_name': full_name,
            'formats_tested': formats_tested,
            'total_formats_available': len(email_formats),
            'found_on_attempt': len(email_formats),  # Used all attempts
            'error': 'No valid email found in any format'
        }

# ========================================
# DATA PROCESSING FUNCTIONS
# ========================================

class DataProcessor:
    """Handle CSV data processing and validation."""
    
    @staticmethod
    def load_csv_file(uploaded_file) -> pd.DataFrame:
        """Load and validate CSV/Excel file."""
        try:
            if uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file)
            return df
        except Exception as e:
            logger.error(f"Failed to load file {uploaded_file.name}: {e}")
            raise
    
    @staticmethod
    def clean_dataframe(df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
        """Clean DataFrame by removing null values and empty strings using mapped columns."""
        # Create a copy with only the mapped columns
        mapped_columns = list(column_mapping.values())
        df_mapped = df[mapped_columns].copy()
        
        # Rename columns to standard names
        reverse_mapping = {v: k for k, v in column_mapping.items()}
        df_mapped = df_mapped.rename(columns=reverse_mapping)
        
        # Remove rows with null values in required columns
        required_fields = list(REQUIRED_FIELDS.keys())
        df_clean = df_mapped.dropna(subset=required_fields).copy()
        
        # Remove rows with empty strings
        for col in required_fields:
            df_clean = df_clean[df_clean[col].astype(str).str.strip() != '']
        
        return df_clean
    
    @staticmethod
    def get_data_stats(df: pd.DataFrame, column_mapping: Dict[str, str] = None) -> Dict[str, int]:
        """Get statistics about the DataFrame."""
        total_rows = len(df)
        
        if column_mapping:
            # Check validity based on mapped columns
            mapped_columns = list(column_mapping.values())
            df_subset = df[mapped_columns]
            valid_rows = len(df_subset.dropna())
        else:
            # Original logic for unmapped data
            valid_rows = total_rows
            
        null_rows = total_rows - valid_rows
        
        return {
            'total_rows': total_rows,
            'valid_rows': valid_rows,
            'null_rows': null_rows
        }

# ========================================
# COLUMN MAPPING FUNCTIONS
# ========================================

def render_column_mapping_interface(df: pd.DataFrame) -> Dict[str, str]:
    """Clean column mapping interface."""
    st.subheader("🔗 Column Mapping")
    
    # Get available columns
    available_columns = [''] + list(df.columns)
    column_mapping = {}
    
    # Create clean 3-column layout
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**First Name**")
        firstname_col = st.selectbox(
            "Select column",
            available_columns,
            key="firstname_mapping",
            label_visibility="collapsed"
        )
        if firstname_col:
            column_mapping['firstname'] = firstname_col
            st.success(f"✓ {firstname_col}")
    
    with col2:
        st.markdown("**Last Name**")
        lastname_col = st.selectbox(
            "Select column", 
            available_columns,
            key="lastname_mapping",
            label_visibility="collapsed"
        )
        if lastname_col:
            column_mapping['lastname'] = lastname_col
            st.success(f"✓ {lastname_col}")
    
    with col3:
        st.markdown("**Company URL**")
        company_col = st.selectbox(
            "Select column",
            available_columns,
            key="company_mapping",
            label_visibility="collapsed"
        )
        if company_col:
            column_mapping['companyURL'] = company_col
            st.success(f"✓ {company_col}")
    
    return column_mapping

def render_mapped_data_preview(df: pd.DataFrame, column_mapping: Dict[str, str]):
    """Clean data preview."""
    if len(column_mapping) == 3:
        # Create preview with mapped columns
        mapped_columns = list(column_mapping.values())
        preview_df = df[mapped_columns].copy()
        
        # Rename for display
        display_mapping = {v: REQUIRED_FIELDS[k] for k, v in column_mapping.items()}
        preview_df = preview_df.rename(columns=display_mapping)
        
        # Show preview in clean format
        with st.expander("📋 Data Preview", expanded=False):
            st.dataframe(preview_df.head(10), use_container_width=True)
        
        return True
    return False

# ========================================
# API KEY DIALOG
# ========================================

@st.dialog("🔑 API Configuration", width="large")
def api_key_dialog():
    """Clean API key input dialog."""
    st.markdown("### Enter your Reoon API Key")
    st.info("Get your API key from: **https://emailverifier.reoon.com/**")
    
    # API key input
    api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="Enter your API key here..."
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Save & Continue", type="primary", use_container_width=True):
            if api_key and validate_api_key(api_key):
                st.session_state.api_key = api_key
                st.session_state.api_key_validated = True
                st.success("API key saved!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Please enter a valid API key")
    
    with col2:
        with st.expander("ℹ️ About this tool"):
            st.markdown("""
            **Features:**
            - Bulk email verification from CSV/Excel
            - Single email verification  
            - Smart email pattern detection
            - Efficient API usage
            """)

# ========================================
# UI COMPONENT RENDERERS
# ========================================

class UIRenderer:
    """Handle UI rendering components."""
    
    @staticmethod
    def render_sidebar():
        """Clean sidebar with minimal information."""
        with st.sidebar:
            # API Status
            if st.session_state.get('api_key_validated', False):
                st.success("🔑 API Connected")
                if st.button("Change API Key", type="secondary", use_container_width=True):
                    st.session_state.api_key = None
                    st.session_state.api_key_validated = False
                    st.rerun()
            else:
                st.error("🔑 No API Key")
            
            st.markdown("---")
            
            # Help section in expander
            with st.expander("📋 File Format Help"):
                st.markdown("""
                **Supported Files:**
                - CSV (.csv)
                - Excel (.xlsx)
                
                **Required Data:**
                - First Name
                - Last Name  
                - Company URL/Domain
                """)
            
            with st.expander("🎯 Email Patterns"):
                st.markdown("""
                **Tested Formats:**
                - firstname.lastname@domain.com
                - firstname@domain.com
                - f.lastname@domain.com
                - flastname@domain.com
                - +10 more patterns...
                """)
            
            return st.session_state.get('api_key')
    
    @staticmethod
    def render_data_preview(df: pd.DataFrame, stats: Dict[str, int]):
        """Render data preview with statistics."""
        st.subheader("📊 Data Preview")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", stats['total_rows'])
        with col2:
            st.metric("Valid Rows", stats['valid_rows'])
        with col3:
            st.metric("Rows with Nulls", stats['null_rows'])
        
        st.dataframe(df.head(10), use_container_width=True)
    
    @staticmethod
    def render_verification_results(verified_emails: List[Dict], total_rows: int, total_api_calls: int):
        """Render verification results with metrics."""
        st.subheader("📈 Verification Results")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Processed", total_rows)
        with col2:
            st.metric("Emails Found", len(verified_emails))
        with col3:
            success_rate = (len(verified_emails) / total_rows * 100) if total_rows > 0 else 0
            st.metric("Success Rate", f"{success_rate:.1f}%")
        with col4:
            avg_calls = total_api_calls / total_rows if total_rows > 0 else 0
            st.metric("Avg API Calls", f"{avg_calls:.1f}")
    
    @staticmethod
    def render_efficiency_insights(results_df: pd.DataFrame):
        """Render algorithm efficiency insights."""
        st.subheader("⚡ Algorithm Efficiency")
        
        attempt_counts = results_df['found_on_attempt'].value_counts().sort_index()
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Emails found by attempt number:**")
            for attempt, count in attempt_counts.items():
                st.write(f"• Attempt {attempt}: {count} emails")
        
        with col2:
            first_attempt_success = len(results_df[results_df['found_on_attempt'] == 1])
            first_attempt_rate = (first_attempt_success / len(results_df) * 100) if len(results_df) > 0 else 0
            st.metric("First Attempt Success", f"{first_attempt_rate:.1f}%")
            
            avg_attempts = results_df['found_on_attempt'].mean()
            st.metric("Avg Attempts to Find", f"{avg_attempts:.1f}")

# ========================================
# TAB CONTENT RENDERERS
# ========================================

def render_csv_upload_tab(api_key: str):
    """Clean CSV upload tab with professional layout."""
    verifier = EmailVerifier(api_key)
    processor = DataProcessor()
    
    # File upload section
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "Upload CSV or Excel File",
            type=['csv', 'xlsx'],
            help="Any column names supported"
        )
    with col2:
        with st.expander("File Requirements"):
            st.markdown("""
            **Required Data:**
            - First names
            - Last names  
            - Company URLs
            
            **Formats:** CSV, Excel
            """)
    
    if uploaded_file is not None:
        try:
            # Load file
            df = processor.load_csv_file(uploaded_file)
            
            # File info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows", len(df))
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                with st.expander("View Columns"):
                    for col in df.columns:
                        st.write(f"• {col}")
            
            # Column mapping
            column_mapping = render_column_mapping_interface(df)
            
            # Validate mapping
            is_mapping_valid, mapping_errors = validate_column_mapping(column_mapping, df.columns.tolist())
            
            if not is_mapping_valid:
                st.error("Please complete column mapping")
                return
            
            # Data preview
            render_mapped_data_preview(df, column_mapping)
            
            # Clean data and show stats
            df_clean = processor.clean_dataframe(df, column_mapping)
            
            if len(df_clean) == 0:
                st.error("No valid data found")
                return
            
            # Processing section
            col1, col2 = st.columns([1, 1])
            with col1:
                st.metric("Ready to Process", len(df_clean))
            with col2:
                start_btn = st.button("🚀 Start Verification", type="primary", use_container_width=True)
            
            if start_btn:
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Results containers
                col1, col2, col3 = st.columns(3)
                with col1:
                    calls_metric = st.empty()
                with col2:
                    found_metric = st.empty()
                with col3:
                    rate_metric = st.empty()
                
                results_container = st.container()
                
                verified_emails = []
                total_rows = len(df_clean)
                total_api_calls = 0
                
                # Process each row
                for index, row in df_clean.iterrows():
                    progress = (index + 1) / total_rows
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {index + 1}/{total_rows}: {row['firstname']} {row['lastname']}")
                    
                    # Verify email
                    result = verifier.verify_single_email(
                        str(row['firstname']).strip(),
                        str(row['lastname']).strip(), 
                        str(row['companyURL']).strip()
                    )
                    
                    if result is not None:
                        found_attempt = result.get('found_on_attempt', 0)
                        total_formats = result.get('total_formats_available', 0)
                        api_calls_used = found_attempt if found_attempt > 0 else total_formats
                        total_api_calls += api_calls_used
                        
                        if result.get('email'):
                            verified_emails.append({
                                'firstname': result['firstname'],
                                'lastname': result['lastname'],
                                'company': result['company'],
                                'email': result['email'],
                                'status': result['status']
                            })
                            
                            with results_container:
                                st.success(f"✅ {result['email']}")
                    
                    # Update metrics
                    calls_metric.metric("API Calls", total_api_calls)
                    found_metric.metric("Emails Found", len(verified_emails))
                    if index + 1 > 0:
                        rate = (len(verified_emails) / (index + 1)) * 100
                        rate_metric.metric("Success Rate", f"{rate:.1f}%")
                
                # Complete
                progress_bar.progress(1.0)
                status_text.success("✅ Verification completed!")
                
                # Results
                if verified_emails:
                    st.subheader("📋 Results")
                    results_df = pd.DataFrame(verified_emails)
                    st.dataframe(results_df, use_container_width=True)
                    
                    # Download
                    csv_buffer = io.StringIO()
                    results_df.to_csv(csv_buffer, index=False)
                    csv_data = csv_buffer.getvalue()
                    
                    st.download_button(
                        "📥 Download Results",
                        data=csv_data,
                        file_name=f"verified_emails_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        type="primary",
                        use_container_width=True
                    )
                    
                    # Stats in expander
                    with st.expander("📊 Detailed Statistics"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Processed", total_rows)
                        with col2:
                            st.metric("Success Rate", f"{(len(verified_emails)/total_rows*100):.1f}%")
                        with col3:
                            st.metric("Avg API Calls", f"{total_api_calls/total_rows:.1f}")
                else:
                    st.warning("No emails found")
                    
        except Exception as e:
            st.error(f"Error: {str(e)}")

def render_single_entry_tab(api_key: str):
    """Clean single entry tab with professional layout."""
    verifier = EmailVerifier(api_key)
    
    # Input form in columns
    col1, col2 = st.columns(2)
    with col1:
        firstname = st.text_input("First Name", placeholder="John")
    with col2:
        lastname = st.text_input("Last Name", placeholder="Smith")
    
    company_url = st.text_input("Company URL", placeholder="company.com")
    
    # Verify button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        verify_btn = st.button("🔍 Verify Email", type="primary", use_container_width=True)
    
    if verify_btn:
        if not all([firstname, lastname, company_url]):
            st.error("Please fill all fields")
            return
        
        with st.spinner("Searching..."):
            result = verifier.verify_single_email(
                firstname.strip(), 
                lastname.strip(), 
                company_url.strip()
            )
            
        # Results
        if result and result.get('email'):
            # Success
            st.markdown(f"""
            <div class="email-found">
                ✅ Email Found: {result['email']}
            </div>
            """, unsafe_allow_html=True)
            
            # Details in columns
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Status", result['status'].title())
            with col2:
                st.metric("Attempts", result.get('found_on_attempt', 'N/A'))
            with col3:
                total = result.get('total_formats_available', 0)
                found = result.get('found_on_attempt', 0)
                if total > 0 and found > 0:
                    saved = ((total - found) / total) * 100
                    st.metric("Efficiency", f"{saved:.0f}%")
            
            # Download single result
            single_df = pd.DataFrame([{
                'firstname': result['firstname'],
                'lastname': result['lastname'],
                'email': result['email'],
                'status': result['status']
            }])
            
            csv_buffer = io.StringIO()
            single_df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            st.download_button(
                "📥 Download Result",
                data=csv_data,
                file_name=f"email_{firstname}_{lastname}_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            # Details in expander
            with st.expander("🔍 Format Details"):
                tested_formats = result.get('formats_tested', [])
                for i, email_format in enumerate(tested_formats, 1):
                    if email_format == result['email']:
                        st.success(f"{i}. {email_format} ✅")
                    else:
                        st.text(f"{i}. {email_format} ❌")
                        
        else:
            # Not found
            st.markdown(f"""
            <div class="email-not-found">
                ❌ No email found for {firstname} {lastname}
            </div>
            """, unsafe_allow_html=True)
            
            if result:
                with st.expander("📋 Formats Tested"):
                    tested_formats = result.get('formats_tested', [])
                    for i, email_format in enumerate(tested_formats, 1):
                        st.text(f"{i}. {email_format}")

# ========================================
# MAIN APPLICATION
# ========================================

def main():
    """Clean main application."""
    # Page setup
    st.set_page_config(**PAGE_CONFIG)
    
    # Session state
    if 'api_key' not in st.session_state:
        st.session_state.api_key = None
    if 'api_key_validated' not in st.session_state:
        st.session_state.api_key_validated = False
    
    # CSS
    load_custom_css()
    
    # Header
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<h1 class="main-header">📧 Email Verifier Pro</h1>', unsafe_allow_html=True)
    
    # API check
    if not st.session_state.get('api_key_validated', False):
        api_key_dialog()
        return
    
    # Sidebar
    renderer = UIRenderer()
    api_key = renderer.render_sidebar()
    
    if not api_key or not validate_api_key(api_key):
        st.error("API validation failed")
        return
    
    # Main tabs
    tab1, tab2 = st.tabs(["📊 Bulk Verification", "👤 Single Verification"])
    
    with tab1:
        render_csv_upload_tab(api_key)
    
    with tab2:
        render_single_entry_tab(api_key)

if __name__ == "__main__":
    main()