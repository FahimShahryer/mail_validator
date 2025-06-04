import streamlit as st
import pandas as pd
import requests
import re
import json
import time
import io
from typing import Tuple, Optional, List

# Set page config
st.set_page_config(
    page_title="Email Enricher",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful UI
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
    
    .upload-box {
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        background: #f8f9ff;
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
</style>
""", unsafe_allow_html=True)

# Core email verification functions (adapted from original code)
def clean_domain(domain_raw: str) -> str:
    """Removes http(s)://, www., and trailing slashes."""
    if not isinstance(domain_raw, str) or not domain_raw.strip():
        return ""
    domain = re.sub(r'^https?://', '', domain_raw.strip(), flags=re.IGNORECASE)
    domain = re.sub(r'^www\.', '', domain, flags=re.IGNORECASE)
    domain = domain.split('/')[0]
    return domain.strip().lower()

def parse_name(full_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Parses a name into first, middle, last."""
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

    first_name = re.sub(r'[^a-z]', '', first_name)
    last_name = re.sub(r'[^a-z]', '', last_name)
    if middle_name: 
        middle_name = re.sub(r'[^a-z]', '', middle_name)

    if len(parts) == 1 and first_name: 
        last_name = first_name
    if not first_name and not last_name: 
        return None, None, None

    return first_name, middle_name, last_name

def generate_email_formats(first_name: str, middle_name: Optional[str], last_name: str, domain: str) -> List[str]:
    """Generates potential email formats."""
    potential_locals = []
    f = first_name[0] if first_name else ''
    m = middle_name[0] if middle_name else ''
    l = last_name[0] if last_name else ''

    if f and last_name: potential_locals.append(f"{f}{last_name}")
    if first_name: potential_locals.append(f"{first_name}")
    if first_name and last_name: potential_locals.append(f"{first_name}.{last_name}")
    if last_name: potential_locals.append(f"{last_name}")
    if f and l: potential_locals.append(f"{f}{l}")
    if first_name and last_name: potential_locals.append(f"{first_name}{last_name}")
    if first_name and l: potential_locals.append(f"{first_name}{l}")
    if last_name and f: potential_locals.append(f"{last_name}{f}")
    if last_name and f: potential_locals.append(f"{last_name}.{f}")
    if f and m and l: potential_locals.append(f"{f}{m}{l}")
    if last_name and first_name: potential_locals.append(f"{last_name}{first_name}")
    if first_name and m and last_name: potential_locals.append(f"{first_name}.{m}.{last_name}")
    if f and m and last_name: potential_locals.append(f"{f}{m}{last_name}")
    if first_name and last_name: potential_locals.append(f"{first_name}_{last_name}")

    generated_emails = list(dict.fromkeys([f"{local_part}@{domain}" for local_part in potential_locals if local_part]))
    return generated_emails

def verify_email_api(email: str, api_key: str) -> dict:
    """Calls the Reoon Email Verifier API."""
    api_url = f"https://emailverifier.reoon.com/api/v1/verify?email={email}&key={api_key}&mode=power"
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API Request Failed: {e}"}
    except json.JSONDecodeError:
        return {"error": "Failed to decode API response"}

def verify_single_email(firstname: str, lastname: str, company_url: str, api_key: str) -> Optional[dict]:
    """Verify email for a single person and return result if valid."""
    # Clean and parse inputs
    domain = clean_domain(company_url)
    if not domain:
        return None
    
    # Combine names
    full_name = f"{firstname} {lastname}".strip()
    first, middle, last = parse_name(full_name)
    
    if not first or not last:
        return None
    
    # Generate email formats
    email_formats = generate_email_formats(first, middle, last, domain)
    
    # Test each format
    forbidden_statuses = ["invalid", "disabled", "unknown"]
    
    for email in email_formats:
        result = verify_email_api(email, api_key)
        
        if result and 'error' not in result:
            status = result.get("status", "unknown")
            if status not in forbidden_statuses:
                return {
                    'firstname': firstname,
                    'lastname': lastname,
                    'company': domain,
                    'email': email,
                    'status': status,
                    'full_name': full_name
                }
        
        # Small delay to avoid rate limiting
        time.sleep(0.3)
    
    return None

# Streamlit App
def main():
    # Header
    st.markdown('<h1 class="main-header">📧 Email Verifier Pro</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Email verification made simple and efficient</p>', unsafe_allow_html=True)
    
    # Sidebar for API key
    with st.sidebar:
        st.header("🔑 Configuration")
        api_key = st.text_input(
            "Enter your Reoon API Key",
            type="password",
            help="Get your API key from https://emailverifier.reoon.com/"
        )
        
        st.markdown("---")
        st.subheader("📋 CSV Format Required")
        st.markdown("""
        Your CSV file should contain these columns:
        - **firstname**: First name
        - **lastname**: Last name  
        - **companyURL**: Company website URL
        
        Example:
        ```
        firstname,lastname,companyURL
        John,Smith,https://company.com
        Jane,Doe,www.example.org
        ```
        """)
        
        st.markdown("---")
        st.subheader("ℹ️ How it works")
        st.markdown("""
        1. Upload your CSV file
        2. Enter your API key
        3. Click 'Start Verification'
        4. Download verified emails
        """)
    
    # Main content area
    if not api_key:
        st.warning("⚠️ Please enter your API key in the sidebar to continue.")
        return
    
    # File upload section
    st.subheader("📁 Upload CSV File")
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=['csv'],
        help="Upload a CSV file with firstname, lastname, and companyURL columns"
    )
    
    if uploaded_file is not None:
        try:
            # Read CSV
            df = pd.read_csv(uploaded_file)
            
            # Validate required columns
            required_columns = ['firstname', 'lastname', 'companyURL']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
                return
            
            # Show preview
            st.subheader("📊 Data Preview")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Rows", len(df))
            with col2:
                valid_rows = len(df.dropna(subset=['firstname', 'lastname', 'companyURL']))
                st.metric("Valid Rows", valid_rows)
            with col3:
                null_rows = len(df) - valid_rows
                st.metric("Rows with Nulls", null_rows)
            
            st.dataframe(df.head(10), use_container_width=True)
            
            # Clean data - remove rows with null values
            df_clean = df.dropna(subset=['firstname', 'lastname', 'companyURL']).copy()
            df_clean = df_clean[
                (df_clean['firstname'].str.strip() != '') & 
                (df_clean['lastname'].str.strip() != '') & 
                (df_clean['companyURL'].str.strip() != '')
            ]
            
            if len(df_clean) == 0:
                st.error("❌ No valid rows found after cleaning. Please check your data.")
                return
            
            st.info(f"📋 {len(df_clean)} rows will be processed (after removing nulls/empty values)")
            
            # Verification section
            st.subheader("🚀 Email Verification")
            
            if st.button("Start Verification", type="primary"):
                # Initialize progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                results_container = st.empty()
                
                verified_emails = []
                total_rows = len(df_clean)
                
                # Process each row
                for index, row in df_clean.iterrows():
                    progress = (index + 1) / total_rows
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {index + 1}/{total_rows}: {row['firstname']} {row['lastname']}")
                    
                    # Verify email
                    result = verify_single_email(
                        str(row['firstname']).strip(),
                        str(row['lastname']).strip(), 
                        str(row['companyURL']).strip(),
                        api_key
                    )
                    
                    if result:
                        verified_emails.append(result)
                        
                        # Update live results
                        with results_container.container():
                            st.success(f"✅ Found: {result['email']} for {result['full_name']}")
                
                # Complete
                progress_bar.progress(1.0)
                status_text.text("✅ Verification completed!")
                
                # Results
                st.subheader("📈 Verification Results")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Processed", total_rows)
                with col2:
                    st.metric("Emails Found", len(verified_emails))
                with col3:
                    success_rate = (len(verified_emails) / total_rows * 100) if total_rows > 0 else 0
                    st.metric("Success Rate", f"{success_rate:.1f}%")
                
                if verified_emails:
                    # Create results DataFrame
                    results_df = pd.DataFrame(verified_emails)
                    results_df = results_df[['firstname', 'lastname', 'company', 'email', 'status']]
                    
                    st.subheader("📋 Verified Emails")
                    st.dataframe(results_df, use_container_width=True)
                    
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
                    
                    st.success(f"🎉 Successfully found {len(verified_emails)} valid email addresses!")
                else:
                    st.warning("⚠️ No valid email addresses were found for the provided data.")
                    
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")

if __name__ == "__main__":
    main()