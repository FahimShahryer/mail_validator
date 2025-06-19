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
    """Render column mapping interface and return the mapping."""
    st.subheader("🔗 Map Your Columns")
    st.info("Please select which columns in your file correspond to the required fields:")
    
    # Get available columns
    available_columns = [''] + list(df.columns)  # Add empty option
    column_mapping = {}
    
    # Create mapping interface
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🧑 First Name**")
        firstname_col = st.selectbox(
            "Select First Name Column",
            available_columns,
            key="firstname_mapping",
            help="Choose the column containing first names"
        )
        if firstname_col:
            column_mapping['firstname'] = firstname_col
            st.success(f"✅ Mapped to: {firstname_col}")
    
    with col2:
        st.markdown("**👤 Last Name**")
        lastname_col = st.selectbox(
            "Select Last Name Column", 
            available_columns,
            key="lastname_mapping",
            help="Choose the column containing last names"
        )
        if lastname_col:
            column_mapping['lastname'] = lastname_col
            st.success(f"✅ Mapped to: {lastname_col}")
    
    with col3:
        st.markdown("**🏢 Company URL**")
        company_col = st.selectbox(
            "Select Company URL Column",
            available_columns,
            key="company_mapping", 
            help="Choose the column containing company URLs/domains"
        )
        if company_col:
            column_mapping['companyURL'] = company_col
            st.success(f"✅ Mapped to: {company_col}")
    
    return column_mapping

def render_mapped_data_preview(df: pd.DataFrame, column_mapping: Dict[str, str]):
    """Show preview of data with mapped columns."""
    if len(column_mapping) == 3:  # All fields mapped
        st.subheader("📋 Data Preview (Mapped Columns)")
        
        # Create preview with mapped columns
        mapped_columns = list(column_mapping.values())
        preview_df = df[mapped_columns].copy()
        
        # Rename for display
        display_mapping = {v: f"{REQUIRED_FIELDS[k]} ({v})" for k, v in column_mapping.items()}
        preview_df = preview_df.rename(columns=display_mapping)
        
        st.dataframe(preview_df.head(10), use_container_width=True)
        
        # Show mapping summary
        st.markdown("**📊 Column Mapping Summary:**")
        for field, display_name in REQUIRED_FIELDS.items():
            if field in column_mapping:
                st.write(f"• **{display_name}** → `{column_mapping[field]}`")
        
        return True
    return False

# ========================================
# API KEY DIALOG
# ========================================

@st.dialog("🔑 API Key Required", width="large")
def api_key_dialog():
    """Modal dialog for API key input."""
    st.markdown("""
    ### Welcome to Email Verifier Pro! 
    
    To get started, please enter your Reoon API key. You can get your API key from:
    👉 **https://emailverifier.reoon.com/**
    """)
    
    # API key input
    api_key = st.text_input(
        "Enter your Reoon API Key",
        type="password",
        placeholder="Enter your API key here...",
        help="Your API key will be stored securely for this session"
    )
    
    # Instructions
    st.markdown("""
    #### 📋 What you can do with this tool:
    - **📊 Flexible CSV Upload**: Use ANY column names - map them after upload!
    - **👤 Single Entry**: Verify email for individual person
    - **🧠 Smart Algorithm**: Tests 10+ email format patterns automatically
    - **⚡ Efficient**: Stops searching when valid email is found
    
    #### 📂 Supported File Formats:
    - ✅ **CSV files** (.csv) with any column names
    - ✅ **Excel files** (.xlsx) with any column names  
    - ✅ **Flexible structure** - you choose which columns to use
    
    #### 🔗 Column Mapping Examples:
    Your file can have columns like:
    ```
    fname, lname, website          →  Map to First Name, Last Name, Company URL
    first_name, surname, domain    →  Map to First Name, Last Name, Company URL  
    FirstName, LastName, Company   →  Map to First Name, Last Name, Company URL
    ```
    """)
    
    # Submit button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Email Verification", type="primary", use_container_width=True):
            if api_key and validate_api_key(api_key):
                st.session_state.api_key = api_key
                st.session_state.api_key_validated = True
                st.success("✅ API key saved successfully!")
                time.sleep(1)  # Brief pause for user feedback
                st.rerun()
            elif not api_key:
                st.error("❌ Please enter your API key")
            else:
                st.error("❌ Please enter a valid API key (minimum 10 characters)")

# ========================================
# UI COMPONENT RENDERERS
# ========================================

class UIRenderer:
    """Handle UI rendering components."""
    
    @staticmethod
    def render_sidebar():
        """Render sidebar with help information only."""
        with st.sidebar:
            st.header("ℹ️ Help & Information")
            
            # Show current API key status
            if st.session_state.get('api_key_validated', False):
                st.success("🔑 API Key: ✅ Active")
                if st.button("🔄 Change API Key", type="secondary"):
                    st.session_state.api_key = None
                    st.session_state.api_key_validated = False
                    st.rerun()
            else:
                st.error("🔑 API Key: ❌ Not Set")
            
            st.markdown("---")
            st.subheader("📋 Flexible CSV Format")
            st.markdown("""
            **Your CSV can have ANY column names!** 
            
            After uploading, you'll map your columns to:
            - **First Name**: Person's first name
            - **Last Name**: Person's last name  
            - **Company URL**: Company website
            
            Examples of supported formats:
            ```csv
            fname,lname,website
            first_name,surname,domain
            FirstName,LastName,CompanyWebsite
            given_name,family_name,url
            ```
            """)
            
            st.markdown("---")
            st.subheader("📊 Supported File Types")
            st.markdown("""
            - ✅ **CSV files** (.csv)
            - ✅ **Excel files** (.xlsx)
            - ✅ **Any column names**
            - ✅ **Flexible structure**
            """)
            
            st.markdown("---")
            st.subheader("🎯 Email Patterns Tested")
            st.markdown("""
            Our algorithm tests multiple patterns:
            - firstname.lastname@domain.com
            - firstname@domain.com
            - f.lastname@domain.com
            - flastname@domain.com
            - And 10+ more formats...
            """)
            
            st.markdown("---")
            st.subheader("⚡ How it works")
            st.markdown("""
            **CSV Mode:**
            1. Upload your CSV file
            2. Click 'Start Verification'
            3. Download verified emails
            
            **Single Entry Mode:**
            1. Enter individual details
            2. Click 'Verify Email'
            3. Get instant results
            """)
            
            st.markdown("---")
            st.info("💡 **Tip**: The algorithm stops testing email formats as soon as it finds a valid one, saving API calls!")
            
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
    """Render CSV upload tab content with flexible column mapping."""
    verifier = EmailVerifier(api_key)
    processor = DataProcessor()
    renderer = UIRenderer()
    
    st.subheader("📁 Upload CSV or Excel File")
    st.info("💡 **New!** Your file can have any column names - you'll map them after upload!")
    
    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=['csv', 'xlsx'],
        help="Upload any CSV or Excel file with names and company information"
    )
    
    if uploaded_file is not None:
        try:
            # Load file
            df = processor.load_csv_file(uploaded_file)
            
            # Show basic file info
            st.success(f"✅ File loaded successfully! Found {len(df)} rows and {len(df.columns)} columns.")
            
            # Show available columns
            with st.expander("📋 View All Columns in Your File", expanded=False):
                st.write("**Available columns:**")
                for i, col in enumerate(df.columns, 1):
                    st.write(f"{i}. `{col}`")
            
            # Column mapping interface
            column_mapping = render_column_mapping_interface(df)
            
            # Validate mapping
            is_mapping_valid, mapping_errors = validate_column_mapping(column_mapping, df.columns.tolist())
            
            if not is_mapping_valid:
                st.error("❌ **Column Mapping Issues:**")
                for error in mapping_errors:
                    st.error(f"• {error}")
                st.warning("Please complete the column mapping to continue.")
                return
            
            # Show mapped data preview
            preview_shown = render_mapped_data_preview(df, column_mapping)
            
            if preview_shown:
                # Get statistics with mapped columns
                stats = processor.get_data_stats(df, column_mapping)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Rows", stats['total_rows'])
                with col2:
                    st.metric("Valid Rows", stats['valid_rows'])
                with col3:
                    st.metric("Rows with Missing Data", stats['null_rows'])
                
                # Clean data with mapping
                df_clean = processor.clean_dataframe(df, column_mapping)
                
                if len(df_clean) == 0:
                    st.error("❌ No valid rows found after cleaning. Please check your data has values in all mapped columns.")
                    return
                
                st.info(f"📋 {len(df_clean)} rows will be processed (after removing missing/empty values)")
                
                # Verification section
                st.subheader("🚀 Email Verification")
                
                if st.button("Start Verification", type="primary", key="csv_verify"):
                    # Initialize progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    results_container = st.empty()
                    efficiency_container = st.empty()
                    
                    verified_emails = []
                    total_rows = len(df_clean)
                    total_api_calls = 0
                    
                    # Process each row (df_clean now has standardized column names)
                    for index, row in df_clean.iterrows():
                        progress = (index + 1) / total_rows
                        progress_bar.progress(progress)
                        status_text.text(f"Processing {index + 1}/{total_rows}: {row['firstname']} {row['lastname']}")
                        
                        # Verify email (using standardized column names)
                        result = verifier.verify_single_email(
                            str(row['firstname']).strip(),
                            str(row['lastname']).strip(), 
                            str(row['companyURL']).strip()
                        )
                        
                        if result is not None:
                            # Track API efficiency - ensure we always have valid integers
                            found_attempt = result.get('found_on_attempt', 0)
                            total_formats = result.get('total_formats_available', 0)
                            
                            # Use the actual attempts made (found_attempt or total if not found)
                            api_calls_used = found_attempt if found_attempt > 0 else total_formats
                            total_api_calls += api_calls_used
                            
                            if result.get('email'):  # Valid email found
                                verified_emails.append({
                                    'firstname': result['firstname'],
                                    'lastname': result['lastname'],
                                    'company': result['company'],
                                    'email': result['email'],
                                    'status': result['status'],
                                    'found_on_attempt': result.get('found_on_attempt', 0),
                                    'total_formats_tested': result.get('total_formats_available', 0)
                                })
                                
                                # Update live results
                                with results_container.container():
                                    st.success(f"✅ Found: {result['email']} for {result['full_name']} (attempt {result.get('found_on_attempt', 'N/A')})")
                        else:
                            # Handle case where domain parsing failed
                            logger.warning(f"Failed to process domain for {row['firstname']} {row['lastname']} - {row['companyURL']}")
                            with results_container.container():
                                st.warning(f"⚠️ Invalid domain for {row['firstname']} {row['lastname']}: {row['companyURL']}")
                        
                        # Update efficiency metrics (moved outside the if-else block)
                        avg_calls_per_person = total_api_calls / (index + 1) if (index + 1) > 0 else 0
                        with efficiency_container.container():
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total API Calls", total_api_calls)
                            with col2:
                                st.metric("Avg Calls/Person", f"{avg_calls_per_person:.1f}")
                            with col3:
                                st.metric("Emails Found", len(verified_emails))
                    
                    # Complete processing
                    progress_bar.progress(1.0)
                    status_text.text("✅ Verification completed!")
                    
                    # Show results
                    renderer.render_verification_results(verified_emails, total_rows, total_api_calls)
                    
                    if verified_emails:
                        # Create results DataFrame
                        results_df = pd.DataFrame(verified_emails)
                        results_df = results_df[['firstname', 'lastname', 'company', 'email', 'status', 'found_on_attempt']]
                        
                        st.subheader("📋 Verified Emails")
                        st.dataframe(results_df, use_container_width=True)
                        
                        # Show efficiency insights
                        renderer.render_efficiency_insights(results_df)
                        
                        # Download button
                        csv_buffer = io.StringIO()
                        results_df.to_csv(csv_buffer, index=False)
                        csv_data = csv_buffer.getvalue()
                        
                        st.download_button(
                            label="📥 Download Verified Emails CSV",
                            data=csv_data,
                            file_name=f"verified_emails_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            type="primary"
                        )
                        
                        # Success message with efficiency summary
                        avg_calls = total_api_calls / total_rows if total_rows > 0 else 0
                        early_stops = sum(1 for result in verified_emails if result['found_on_attempt'] < result['total_formats_tested'])
                        
                        st.success(f"🎉 Successfully found {len(verified_emails)} valid email addresses!")
                        st.info(f"💡 **Efficiency:** Used {total_api_calls} API calls total (avg {avg_calls:.1f} per person). Algorithm stopped early {early_stops} times when valid emails were found.")
                        
                        # Show column mapping used
                        with st.expander("📊 Column Mapping Used"):
                            for field, display_name in REQUIRED_FIELDS.items():
                                original_col = column_mapping[field]
                                st.write(f"• **{display_name}** ← `{original_col}` (from your file)")
                    else:
                        st.warning("⚠️ No valid email addresses were found for the provided data.")
                        
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            st.error(f"❌ Error processing file: {str(e)}")
            st.info("💡 **Tips:** Make sure your file is a valid CSV or Excel file with readable data.")

def render_single_entry_tab(api_key: str):
    """Render single entry verification tab content."""
    verifier = EmailVerifier(api_key)
    
    st.subheader("👤 Single Email Verification")
    
    # Input form
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            firstname = st.text_input(
                "First Name",
                placeholder="e.g., John",
                help="Enter the person's first name"
            )
        
        with col2:
            lastname = st.text_input(
                "Last Name", 
                placeholder="e.g., Smith",
                help="Enter the person's last name"
            )
        
        company_url = st.text_input(
            "Company URL",
            placeholder="e.g., https://company.com or company.com",
            help="Enter the company website URL"
        )
        
        # Verify button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            verify_btn = st.button(
                "🔍 Verify Email", 
                type="primary",
                use_container_width=True,
                key="single_verify"
            )
    
    # Verification logic
    if verify_btn:
        # Validate inputs
        if not all([firstname, lastname, company_url]):
            st.error("❌ Please fill in all fields (First Name, Last Name, and Company URL)")
            return
        
        # Show processing
        with st.spinner("🔍 Searching for email address..."):
            # Clean inputs
            firstname_clean = firstname.strip()
            lastname_clean = lastname.strip()
            company_url_clean = company_url.strip()
            
            # Verify email
            result = verifier.verify_single_email(firstname_clean, lastname_clean, company_url_clean)
            
        # Display results
        st.subheader("🎯 Verification Results")
        
        if result and result.get('email'):
            # Email found - success case
            st.markdown(f"""
            <div class="email-found">
                ✅ Email Found!<br>
                📧 {result['email']}
            </div>
            """, unsafe_allow_html=True)
            
            # Detailed results
            st.markdown(f"""
            <div class="result-card">
                <h3>📋 Verification Details</h3>
                <p><strong>👤 Full Name:</strong> {result['full_name']}</p>
                <p><strong>🏢 Company:</strong> {result['company']}</p>
                <p><strong>📧 Email:</strong> {result['email']}</p>
                <p><strong>✅ Status:</strong> {result['status'].title()}</p>
                <p><strong>⚡ Found on attempt:</strong> {result.get('found_on_attempt', 'N/A')} of {result.get('total_formats_available', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Efficiency metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("API Calls Used", result.get('found_on_attempt', 'N/A'))
            with col2:
                st.metric("Total Formats Available", result.get('total_formats_available', 'N/A'))
            with col3:
                total_formats = result.get('total_formats_available', 0)
                found_attempt = result.get('found_on_attempt', 0)
                
                if total_formats > 0 and found_attempt > 0:
                    efficiency = ((total_formats - found_attempt) / total_formats) * 100
                    st.metric("API Calls Saved", f"{efficiency:.0f}%")
                else:
                    st.metric("API Calls Saved", "N/A")
            
            # Show tested formats
            with st.expander("🔍 View Tested Email Formats"):
                tested_formats = result.get('formats_tested', [])
                for i, email_format in enumerate(tested_formats, 1):
                    if email_format == result['email']:
                        st.success(f"{i}. {email_format} ✅ (Valid - Search stopped here)")
                    else:
                        st.text(f"{i}. {email_format} ❌")
                
                untested_count = result.get('total_formats_available', 0) - len(tested_formats)
                if untested_count > 0:
                    st.info(f"💡 **Efficiency gain:** {untested_count} additional formats were not tested because a valid email was found early!")
            
            # Download single result
            single_result_df = pd.DataFrame([{
                'firstname': result['firstname'],
                'lastname': result['lastname'], 
                'company': result['company'],
                'email': result['email'],
                'status': result['status'],
                'found_on_attempt': result.get('found_on_attempt', 0),
                'api_calls_saved': max(0, result.get('total_formats_available', 0) - result.get('found_on_attempt', 0))
            }])
            
            csv_buffer = io.StringIO()
            single_result_df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            st.download_button(
                label="📥 Download Result as CSV",
                data=csv_data,
                file_name=f"email_verification_{firstname_clean}_{lastname_clean}_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                type="secondary"
            )
            
        else:
            # Email not found - failure case
            st.markdown(f"""
            <div class="email-not-found">
                ❌ No Valid Email Found<br>
                for {firstname_clean} {lastname_clean} at {verifier.clean_domain(company_url_clean)}
            </div>
            """, unsafe_allow_html=True)
            
            if result:
                # Show what was tested
                with st.expander("🔍 View All Tested Email Formats"):
                    tested_formats = result.get('formats_tested', [])
                    st.info(f"Tested {len(tested_formats)} different email formats:")
                    for i, email_format in enumerate(tested_formats, 1):
                        st.text(f"{i}. {email_format} ❌")
                    
                    st.info("💡 **Tip:** The email might not exist, or the person might use a different email format not covered by our algorithm.")
            else:
                st.error("❌ Invalid company URL provided. Please check the URL format.")

# ========================================
# MAIN APPLICATION
# ========================================

def main():
    """Main application entry point."""
    # Set page configuration
    st.set_page_config(**PAGE_CONFIG)
    
    # Initialize session state
    if 'api_key' not in st.session_state:
        st.session_state.api_key = None
    if 'api_key_validated' not in st.session_state:
        st.session_state.api_key_validated = False
    
    # Load custom CSS
    load_custom_css()
    
    # Header
    st.markdown('<h1 class="main-header">📧 Email Verifier Pro</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Professional email verification made simple and efficient</p>', unsafe_allow_html=True)
    
    # Check if API key is set, if not show dialog
    if not st.session_state.get('api_key_validated', False):
        api_key_dialog()
        return  # Don't show the rest of the app until API key is set
    
    # Render sidebar (now just for help/info)
    renderer = UIRenderer()
    api_key = renderer.render_sidebar()
    
    # Validate API key (should always be valid at this point, but double-check)
    if not api_key or not validate_api_key(api_key):
        st.error("❌ API key validation failed. Please refresh the page.")
        if st.button("🔄 Reset API Key"):
            st.session_state.api_key = None
            st.session_state.api_key_validated = False
            st.rerun()
        return
    
    # Main content tabs
    tab1, tab2 = st.tabs(["📁 CSV Upload", "👤 Single Entry"])
    
    with tab1:
        render_csv_upload_tab(api_key)
    
    with tab2:
        render_single_entry_tab(api_key)

if __name__ == "__main__":
    main()