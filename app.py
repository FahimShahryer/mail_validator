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
    
    .single-entry-form {
        background: #f8f9ff;
        padding: 2rem;
        border-radius: 15px;
        border: 1px solid #e0e6ff;
        margin: 1rem 0;
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
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px 10px 0 0;
        padding: 1rem 2rem;
        font-weight: bold;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(90deg, #764ba2 0%, #667eea 100%);
    }
</style>
""", unsafe_allow_html=True)

# Core email verification functions (same as before)
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
                    'full_name': full_name,
                    'all_formats_tested': email_formats
                }
        
        # Small delay to avoid rate limiting
        time.sleep(0.3)
    
    return None

def render_csv_upload_tab(api_key: str):
    """Renders the CSV upload tab content."""
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
            
            if st.button("Start Verification", type="primary", key="csv_verify"):
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

def render_single_entry_tab(api_key: str):
    """Renders the single entry verification tab content."""
    st.subheader("👤 Single Email Verification")
    
    # Create a form container
    with st.container():
        st.markdown('<div class="single-entry-form">', unsafe_allow_html=True)
        
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
        
        st.markdown('</div>', unsafe_allow_html=True)
        
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
        if not firstname or not lastname or not company_url:
            st.error("❌ Please fill in all fields (First Name, Last Name, and Company URL)")
            return
        
        # Show processing
        with st.spinner("🔍 Searching for email address..."):
            # Clean inputs
            firstname_clean = firstname.strip()
            lastname_clean = lastname.strip()
            company_url_clean = company_url.strip()
            
            # Verify email
            result = verify_single_email(firstname_clean, lastname_clean, company_url_clean, api_key)
            
        # Display results
        st.subheader("🎯 Verification Results")
        
        if result:
            # Email found
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
            </div>
            """, unsafe_allow_html=True)
            
            # Show tested formats
            with st.expander("🔍 View All Tested Email Formats"):
                tested_formats = result.get('all_formats_tested', [])
                for i, email_format in enumerate(tested_formats, 1):
                    if email_format == result['email']:
                        st.success(f"{i}. {email_format} ✅ (Valid)")
                    else:
                        st.text(f"{i}. {email_format}")
            
            # Download single result
            single_result_df = pd.DataFrame([{
                'firstname': result['firstname'],
                'lastname': result['lastname'], 
                'company': result['company'],
                'email': result['email'],
                'status': result['status']
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
            # Email not found
            st.markdown(f"""
            <div class="email-not-found">
                ❌ No Valid Email Found<br>
                for {firstname_clean} {lastname_clean} at {clean_domain(company_url_clean)}
            </div>
            """, unsafe_allow_html=True)
            
            # Show what was tested
            domain = clean_domain(company_url_clean)
            if domain:
                full_name = f"{firstname_clean} {lastname_clean}"
                first, middle, last = parse_name(full_name)
                
                if first and last:
                    tested_formats = generate_email_formats(first, middle, last, domain)
                    
                    with st.expander("🔍 View All Tested Email Formats"):
                        st.info(f"Tested {len(tested_formats)} different email formats:")
                        for i, email_format in enumerate(tested_formats, 1):
                            st.text(f"{i}. {email_format}")
                    
                    st.info("💡 **Tip:** The email might not exist, or the person might use a different email format not covered by our algorithm.")
            else:
                st.error("❌ Invalid company URL provided. Please check the URL format.")

# Main Streamlit App
def main():
    # Header
    st.markdown('<h1 class="main-header">📧 Email Verifier Pro</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Professional email verification made simple and efficient</p>', unsafe_allow_html=True)
    
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
        **CSV Mode:**
        1. Upload your CSV file
        2. Enter your API key
        3. Click 'Start Verification'
        4. Download verified emails
        
        **Single Entry Mode:**
        1. Enter individual details
        2. Click 'Verify Email'
        3. Get instant results
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
    
    # Main content area
    if not api_key:
        st.warning("⚠️ Please enter your API key in the sidebar to continue.")
        return
    
    # Tab structure
    tab1, tab2 = st.tabs(["📁 CSV Upload", "👤 Single Entry"])
    
    with tab1:
        render_csv_upload_tab(api_key)
    
    with tab2:
        render_single_entry_tab(api_key)

if __name__ == "__main__":
    main()