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
    "page_title": "Mail Validator",
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

# CSV required columns
REQUIRED_CSV_COLUMNS = ['firstname', 'lastname', 'companyURL']

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

def validate_csv_columns(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Validate CSV has required columns."""
    missing_columns = [col for col in REQUIRED_CSV_COLUMNS if col not in df.columns]
    return len(missing_columns) == 0, missing_columns

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
    def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Clean DataFrame by removing null values and empty strings."""
        # Remove rows with null values in required columns
        df_clean = df.dropna(subset=REQUIRED_CSV_COLUMNS).copy()
        
        # Remove rows with empty strings
        for col in REQUIRED_CSV_COLUMNS:
            df_clean = df_clean[df_clean[col].astype(str).str.strip() != '']
        
        return df_clean
    
    @staticmethod
    def get_data_stats(df: pd.DataFrame) -> Dict[str, int]:
        """Get statistics about the DataFrame."""
        total_rows = len(df)
        valid_rows = len(df.dropna(subset=REQUIRED_CSV_COLUMNS))
        null_rows = total_rows - valid_rows
        
        return {
            'total_rows': total_rows,
            'valid_rows': valid_rows,
            'null_rows': null_rows
        }

# ========================================
# API KEY DIALOG
# ========================================

@st.dialog("🔑 API Key Required", width="large")
def api_key_dialog():
    """Modal dialog for API key input."""
    st.markdown("""
    ### Welcome to Mail Validator! 
    
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
    - **CSV Upload**: Verify emails for multiple people from a CSV/Excel file
    - **Single Entry**: Verify email for individual person
    - **Smart Algorithm**: Tests 10+ email format patterns automatically
    - **Efficient**: Stops searching when valid email is found
    
    #### 📊 CSV Format Required:
    ```csv
    firstname,lastname,companyURL
    John,Smith,https://company.com
    Jane,Doe,www.example.org
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
            st.header("Mail Validator")
            
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
            st.subheader("📋 CSV Format Required")
            st.markdown("""
            Your CSV file should contain these columns:
            - **firstname**: First name
            - **lastname**: Last name  
            - **companyURL**: Company website URL
            
            Example:
            ```csv
            firstname,lastname,companyURL
            John,Smith,https://company.com
            Jane,Doe,www.example.org
            ```
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
    """Render CSV upload tab content."""
    verifier = EmailVerifier(api_key)
    processor = DataProcessor()
    renderer = UIRenderer()
    
    st.subheader("📁 Upload CSV File")
    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=['csv', 'xlsx'],
        help="Upload a CSV or Excel file with firstname, lastname, and companyURL columns"
    )
    
    if uploaded_file is not None:
        try:
            # Load and validate file
            df = processor.load_csv_file(uploaded_file)
            
            # Validate required columns
            is_valid, missing_columns = validate_csv_columns(df)
            if not is_valid:
                st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
                return
            
            # Get statistics and show preview
            stats = processor.get_data_stats(df)
            renderer.render_data_preview(df, stats)
            
            # Clean data
            df_clean = processor.clean_dataframe(df)
            
            if len(df_clean) == 0:
                st.error("❌ No valid rows found after cleaning. Please check your data.")
                return
            
            st.info(f"📋 {len(df_clean)} rows will be processed (after removing nulls/empty values)")
            
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
                else:
                    st.warning("⚠️ No valid email addresses were found for the provided data.")
                    
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            st.error(f"❌ Error processing file: {str(e)}")

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
    
    # # Header
    # st.markdown('<h1 class="main-header">📧 Email Verifier Pro</h1>', unsafe_allow_html=True)
    # st.markdown('<p class="sub-header">Professional email verification made simple and efficient</p>', unsafe_allow_html=True)
    
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