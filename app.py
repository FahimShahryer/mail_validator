import streamlit as st
import pandas as pd
import requests
import re
import json
import time
import io
from typing import Tuple, Optional, List, Dict
from urllib.parse import urlparse

# Set page config
st.set_page_config(
    page_title="Email Verifier Pro",
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
</style>
""", unsafe_allow_html=True)

# ========================================
# CORE EMAIL VERIFICATION FUNCTIONS
# ========================================

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
    """Verify email for a single person and return result immediately when valid email is found."""
    # Clean and parse inputs
    domain = clean_domain(company_url)
    if not domain:
        return {
            'firstname': firstname,
            'lastname': lastname,
            'company': domain or 'unknown',
            'email': None,
            'status': 'invalid_domain',
            'full_name': f"{firstname} {lastname}".strip(),
            'formats_tested': [],
            'total_formats_available': 0,
            'found_on_attempt': None,
            'error': 'Invalid domain provided'
        }
    
    # Combine names
    full_name = f"{firstname} {lastname}".strip()
    first, middle, last = parse_name(full_name)
    
    if not first or not last:
        return {
            'firstname': firstname,
            'lastname': lastname,
            'company': domain,
            'email': None,
            'status': 'invalid_names',
            'full_name': full_name,
            'formats_tested': [],
            'total_formats_available': 0,
            'found_on_attempt': None,
            'error': 'Could not parse first and last names'
        }
    
    # Generate email formats
    email_formats = generate_email_formats(first, middle, last, domain)
    
    # Track which formats were actually tested
    formats_tested = []
    forbidden_statuses = ["invalid", "disabled", "unknown"]
    
    # Test each format until we find a valid one
    for i, email in enumerate(email_formats):
        formats_tested.append(email)
        
        try:
            result = verify_email_api(email, api_key)
            
            if result and 'error' not in result:
                status = result.get("status", "unknown")
                
                # If status is valid (not in forbidden list), return immediately
                if status not in forbidden_statuses:
                    return {
                        'firstname': firstname,
                        'lastname': lastname,
                        'company': domain,
                        'email': email,
                        'status': status,
                        'full_name': full_name,
                        'formats_tested': formats_tested,
                        'total_formats_available': len(email_formats),
                        'found_on_attempt': len(formats_tested),  # This is always an integer
                        'api_result': result
                    }
            
            # If this format didn't work and we have more to test, add delay
            if i < len(email_formats) - 1:
                time.sleep(0.3)
                
        except Exception as e:
            # Log API error but continue with next format
            print(f"API error for {email}: {str(e)}")
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
        'found_on_attempt': None,  # Explicitly None when not found
        'error': 'No valid email found in any format'
    }

# ========================================
# SMART COLUMN DETECTION FUNCTIONS
# ========================================

def analyze_column_content(df: pd.DataFrame, column: str, sample_size: int = 50) -> Dict:
    """Analyze the content of a column to determine its likely type."""
    if column not in df.columns:
        return {"type": "unknown", "confidence": 0, "analysis": {}}
    
    # Get sample data (non-null values)
    sample_data = df[column].dropna().astype(str).head(sample_size).tolist()
    
    if not sample_data:
        return {"type": "unknown", "confidence": 0, "analysis": {"reason": "no_data"}}
    
    analysis = {
        "total_samples": len(sample_data),
        "avg_length": sum(len(str(x)) for x in sample_data) / len(sample_data),
        "has_spaces": sum(1 for x in sample_data if ' ' in str(x)),
        "has_dots": sum(1 for x in sample_data if '.' in str(x)),
        "has_at_symbol": sum(1 for x in sample_data if '@' in str(x)),
        "has_http": sum(1 for x in sample_data if str(x).lower().startswith(('http', 'www'))),
        "has_common_tlds": sum(1 for x in sample_data if any(tld in str(x).lower() for tld in ['.com', '.org', '.net', '.io', '.co', '.gov', '.edu'])),
        "numeric_count": sum(1 for x in sample_data if str(x).replace('.', '').replace('-', '').isdigit()),
        "single_words": sum(1 for x in sample_data if len(str(x).split()) == 1),
        "multiple_words": sum(1 for x in sample_data if len(str(x).split()) > 1)
    }
    
    # Calculate percentages
    total = len(sample_data)
    percentages = {k: (v / total * 100) if total > 0 else 0 for k, v in analysis.items() if isinstance(v, (int, float))}
    
    # Determine column type based on content analysis
    confidence = 0
    column_type = "unknown"
    
    # URL/Website detection
    if (percentages["has_common_tlds"] > 60 or 
        percentages["has_http"] > 30 or 
        percentages["has_dots"] > 70):
        column_type = "url"
        confidence = min(90, percentages["has_common_tlds"] + percentages["has_http"])
    
    # Email detection
    elif percentages["has_at_symbol"] > 70:
        column_type = "email"
        confidence = min(95, percentages["has_at_symbol"])
    
    # First/Last name detection
    elif (percentages["single_words"] > 70 and 
          percentages["avg_length"] < 15 and 
          percentages["has_spaces"] < 20):
        column_type = "name"
        confidence = 70
    
    # Full name detection
    elif (percentages["multiple_words"] > 50 and 
          percentages["has_spaces"] > 40 and 
          percentages["avg_length"] > 8):
        column_type = "full_name"
        confidence = 75
    
    return {
        "type": column_type,
        "confidence": confidence,
        "analysis": analysis,
        "percentages": percentages,
        "sample_values": sample_data[:5]
    }

def smart_column_detection(df: pd.DataFrame) -> Dict[str, Dict]:
    """Smart detection of firstname, lastname, and company URL columns."""
    
    results = {
        "firstname": {"column": None, "confidence": 0, "candidates": []},
        "lastname": {"column": None, "confidence": 0, "candidates": []},
        "company_url": {"column": None, "confidence": 0, "candidates": []}
    }
    
    # Define column name patterns
    firstname_patterns = [
        r'^(first|fname|firstname|first_name|given|given_name|forename)$',
        r'^f_?name$',
        r'^(prenom|nome|vorname)$',  # International
        r'first'
    ]
    
    lastname_patterns = [
        r'^(last|lname|lastname|last_name|surname|family|family_name)$',
        r'^l_?name$',
        r'^(nom|apellido|nachname)$',  # International
        r'last|surname'
    ]
    
    url_patterns = [
        r'^(url|website|site|domain|company_?url|company_?website)$',
        r'^(web|link|homepage|www)$',
        r'(company|corp|business).*(url|site|web)',
        r'website|domain|url'
    ]
    
    # Analyze each column
    for column in df.columns:
        column_lower = column.lower().strip()
        content_analysis = analyze_column_content(df, column)
        
        # Check firstname patterns
        firstname_score = 0
        for pattern in firstname_patterns:
            if re.search(pattern, column_lower, re.IGNORECASE):
                firstname_score = 90 if re.match(pattern.replace('$', '').replace('^', ''), column_lower) else 70
                break
        
        # Boost score if content looks like single names
        if content_analysis["type"] == "name":
            firstname_score = max(firstname_score, content_analysis["confidence"])
        
        if firstname_score > 0:
            results["firstname"]["candidates"].append({
                "column": column,
                "score": firstname_score,
                "reason": f"Pattern match + content analysis",
                "content_type": content_analysis["type"]
            })
        
        # Check lastname patterns
        lastname_score = 0
        for pattern in lastname_patterns:
            if re.search(pattern, column_lower, re.IGNORECASE):
                lastname_score = 90 if re.match(pattern.replace('$', '').replace('^', ''), column_lower) else 70
                break
        
        if content_analysis["type"] == "name":
            lastname_score = max(lastname_score, content_analysis["confidence"])
        
        if lastname_score > 0:
            results["lastname"]["candidates"].append({
                "column": column,
                "score": lastname_score,
                "reason": f"Pattern match + content analysis",
                "content_type": content_analysis["type"]
            })
        
        # Check URL patterns
        url_score = 0
        for pattern in url_patterns:
            if re.search(pattern, column_lower, re.IGNORECASE):
                url_score = 90 if re.match(pattern.replace('$', '').replace('^', ''), column_lower) else 70
                break
        
        if content_analysis["type"] == "url":
            url_score = max(url_score, content_analysis["confidence"])
        
        if url_score > 0:
            results["company_url"]["candidates"].append({
                "column": column,
                "score": url_score,
                "reason": f"Pattern match + content analysis",
                "content_type": content_analysis["type"]
            })
    
    # Sort candidates by score and pick the best ones
    for field_type in results:
        if results[field_type]["candidates"]:
            results[field_type]["candidates"].sort(key=lambda x: x["score"], reverse=True)
            best_candidate = results[field_type]["candidates"][0]
            results[field_type]["column"] = best_candidate["column"]
            results[field_type]["confidence"] = best_candidate["score"]
    
    return results

# ========================================
# USER INTERFACE FUNCTIONS
# ========================================

def render_column_confirmation_dialog(df: pd.DataFrame, detection_results: Dict) -> Dict[str, str]:
    """Render confirmation dialog for column detection."""
    
    st.subheader("🔍 Smart Column Detection Results")
    
    # Show detection confidence
    col1, col2, col3 = st.columns(3)
    
    with col1:
        firstname_confidence = detection_results["firstname"]["confidence"]
        if firstname_confidence > 70:
            st.success(f"✅ First Name: {firstname_confidence:.0f}% confident")
        elif firstname_confidence > 40:
            st.warning(f"⚠️ First Name: {firstname_confidence:.0f}% confident")
        else:
            st.error("❌ First Name: Not detected")
    
    with col2:
        lastname_confidence = detection_results["lastname"]["confidence"]
        if lastname_confidence > 70:
            st.success(f"✅ Last Name: {lastname_confidence:.0f}% confident")
        elif lastname_confidence > 40:
            st.warning(f"⚠️ Last Name: {lastname_confidence:.0f}% confident")
        else:
            st.error("❌ Last Name: Not detected")
    
    with col3:
        url_confidence = detection_results["company_url"]["confidence"]
        if url_confidence > 70:
            st.success(f"✅ Company URL: {url_confidence:.0f}% confident")
        elif url_confidence > 40:
            st.warning(f"⚠️ Company URL: {url_confidence:.0f}% confident")
        else:
            st.error("❌ Company URL: Not detected")
    
    # Show recommendations
    st.subheader("🎯 Recommended Column Mapping")
    
    recommendations = {}
    
    # Get recommended columns
    recommended_firstname = detection_results["firstname"]["column"]
    recommended_lastname = detection_results["lastname"]["column"]
    recommended_url = detection_results["company_url"]["column"]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if recommended_firstname:
            st.info(f"**First Name:** `{recommended_firstname}`")
            sample_values = df[recommended_firstname].dropna().head(3).tolist()
            st.caption(f"Sample: {', '.join(map(str, sample_values))}")
        else:
            st.error("**First Name:** Not detected")
    
    with col2:
        if recommended_lastname:
            st.info(f"**Last Name:** `{recommended_lastname}`")
            sample_values = df[recommended_lastname].dropna().head(3).tolist()
            st.caption(f"Sample: {', '.join(map(str, sample_values))}")
        else:
            st.error("**Last Name:** Not detected")
    
    with col3:
        if recommended_url:
            st.info(f"**Company URL:** `{recommended_url}`")
            sample_values = df[recommended_url].dropna().head(3).tolist()
            st.caption(f"Sample: {', '.join(map(str, sample_values))}")
        else:
            st.error("**Company URL:** Not detected")
    
    # Show detection details
    with st.expander("🔍 View Detection Details"):
        for field_type, result in detection_results.items():
            if result["candidates"]:
                st.write(f"**{field_type.replace('_', ' ').title()} Candidates:**")
                for i, candidate in enumerate(result["candidates"][:3]):  # Show top 3
                    confidence_emoji = "🟢" if candidate["score"] > 70 else "🟡" if candidate["score"] > 40 else "🔴"
                    st.write(f"{confidence_emoji} `{candidate['column']}` - {candidate['score']:.0f}% ({candidate['reason']})")
    
    # Confirmation buttons
    st.subheader("✅ Confirm Column Mapping")
    
    col1, col2 = st.columns(2)
    
    with col1:
        accept_recommendations = st.button(
            "✅ Accept Recommendations", 
            type="primary",
            disabled=not all([recommended_firstname, recommended_lastname, recommended_url]),
            help="Use the automatically detected columns"
        )
    
    with col2:
        manual_selection = st.button(
            "🔧 Manual Selection", 
            type="secondary",
            help="Choose columns manually"
        )
    
    # Handle user choice
    if accept_recommendations:
        recommendations = {
            'firstname': recommended_firstname,
            'lastname': recommended_lastname,
            'companyURL': recommended_url,
            'method': 'automatic'
        }
        st.session_state['column_mapping'] = recommendations
        st.session_state['mapping_confirmed'] = True
        st.rerun()
    
    elif manual_selection:
        st.session_state['show_manual_selection'] = True
        st.rerun()
    
    return recommendations

def render_manual_column_selection(df: pd.DataFrame) -> Dict[str, str]:
    """Render manual column selection interface."""
    
    st.subheader("🔧 Manual Column Selection")
    st.info("Please select the correct columns for each field:")
    
    available_columns = [""] + list(df.columns)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        firstname_col = st.selectbox(
            "First Name Column",
            available_columns,
            help="Select the column containing first names"
        )
        if firstname_col:
            sample_values = df[firstname_col].dropna().head(3).tolist()
            st.caption(f"Sample: {', '.join(map(str, sample_values))}")
    
    with col2:
        lastname_col = st.selectbox(
            "Last Name Column",
            available_columns,
            help="Select the column containing last names"
        )
        if lastname_col:
            sample_values = df[lastname_col].dropna().head(3).tolist()
            st.caption(f"Sample: {', '.join(map(str, sample_values))}")
    
    with col3:
        url_col = st.selectbox(
            "Company URL Column",
            available_columns,
            help="Select the column containing company URLs/websites"
        )
        if url_col:
            sample_values = df[url_col].dropna().head(3).tolist()
            st.caption(f"Sample: {', '.join(map(str, sample_values))}")
    
    # Validation and confirmation
    all_selected = firstname_col and lastname_col and url_col
    
    if all_selected:
        # Check for duplicate selections
        selected_cols = [firstname_col, lastname_col, url_col]
        if len(set(selected_cols)) != len(selected_cols):
            st.error("❌ Please select different columns for each field")
            return {}
        
        st.success("✅ All columns selected!")
        
        if st.button("Confirm Manual Selection", type="primary"):
            mapping = {
                'firstname': firstname_col,
                'lastname': lastname_col,
                'companyURL': url_col,
                'method': 'manual'
            }
            st.session_state['column_mapping'] = mapping
            st.session_state['mapping_confirmed'] = True
            st.session_state['show_manual_selection'] = False
            st.rerun()
    else:
        st.warning("⚠️ Please select all required columns")
    
    # Back button
    if st.button("← Back to Recommendations"):
        st.session_state['show_manual_selection'] = False
        st.rerun()
    
    return {}

def run_smart_verification(df: pd.DataFrame, api_key: str):
    """Run the smart email verification process with proper error handling and progress tracking."""
    
    # Initialize progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.empty()
    efficiency_container = st.empty()
    
    verified_emails = []
    total_rows = len(df)
    total_api_calls = 0
    
    # Reset the DataFrame index to ensure proper iteration
    df_reset = df.reset_index(drop=True)
    
    # Process each row with proper progress tracking
    for row_num, (index, row) in enumerate(df_reset.iterrows()):
        # Use row_num (0-based counter) instead of index for progress calculation
        progress = min((row_num + 1) / total_rows, 1.0)  # Ensure progress never exceeds 1.0
        progress_bar.progress(progress)
        
        status_text.text(f"Processing {row_num + 1}/{total_rows}: {row['firstname']} {row['lastname']}")
        
        try:
            # Verify email using the improved algorithm
            result = verify_single_email(
                str(row['firstname']).strip(),
                str(row['lastname']).strip(), 
                str(row['companyURL']).strip(),
                api_key
            )
            
            if result:
                # Handle None values properly when tracking API efficiency
                found_on_attempt = result.get('found_on_attempt') or 0
                total_formats_available = result.get('total_formats_available') or 0
                
                # Use the actual attempts made, or fall back to total available
                api_calls_used = found_on_attempt if found_on_attempt > 0 else total_formats_available
                
                # Ensure we're adding integers only
                if isinstance(api_calls_used, (int, float)) and api_calls_used > 0:
                    total_api_calls += int(api_calls_used)
                else:
                    # Fallback: assume 1 API call was made
                    total_api_calls += 1
                
                if result.get('email'):  # Valid email found
                    verified_emails.append({
                        'firstname': result['firstname'],
                        'lastname': result['lastname'],
                        'company': result['company'],
                        'email': result['email'],
                        'status': result['status'],
                        'found_on_attempt': found_on_attempt if found_on_attempt > 0 else 1,
                        'total_formats_tested': total_formats_available if total_formats_available > 0 else 1
                    })
                    
                    # Update live results
                    with results_container.container():
                        attempt_text = f"(attempt {found_on_attempt})" if found_on_attempt > 0 else ""
                        st.success(f"✅ Found: {result['email']} for {result.get('full_name', 'Unknown')} {attempt_text}")
            else:
                # If result is None, still count 1 API call attempt
                total_api_calls += 1
            
            # Update efficiency metrics (use row_num + 1 for proper calculation)
            processed_count = row_num + 1
            avg_calls_per_person = total_api_calls / processed_count if processed_count > 0 else 0
            
            # Update efficiency display every 5 rows to avoid too many updates
            if processed_count % 5 == 0 or processed_count == total_rows:
                with efficiency_container.container():
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total API Calls", total_api_calls)
                    with col2:
                        st.metric("Avg Calls/Person", f"{avg_calls_per_person:.1f}")
                    with col3:
                        st.metric("Emails Found", len(verified_emails))
        
        except Exception as e:
            # Handle individual row processing errors
            st.error(f"Error processing {row['firstname']} {row['lastname']}: {str(e)}")
            total_api_calls += 1  # Count as 1 attempt even if failed
            continue
    
    # Complete - ensure progress is exactly 1.0
    progress_bar.progress(1.0)
    status_text.text("✅ Smart verification completed!")
    
    # Final results
    st.subheader("📈 Smart Verification Results")
    
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
    
    if verified_emails:
        # Create results DataFrame
        results_df = pd.DataFrame(verified_emails)
        results_df = results_df[['firstname', 'lastname', 'company', 'email', 'status', 'found_on_attempt']]
        
        st.subheader("📋 Verified Emails")
        st.dataframe(results_df, use_container_width=True)
        
        # Efficiency insights (only show if we have results)
        if len(results_df) > 0:
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
        
        # Download button
        csv_buffer = io.StringIO()
        results_df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            label="📥 Download Verified Emails CSV",
            data=csv_data,
            file_name=f"smart_verified_emails_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            type="primary"
        )
        
        # Calculate efficiency
        max_possible_calls = total_rows * 10  # Assuming max 10 formats per person
        api_efficiency = ((max_possible_calls - total_api_calls) / max_possible_calls * 100) if max_possible_calls > 0 else 0
        
        st.success(f"🎉 Smart verification found {len(verified_emails)} valid email addresses!")
        st.info(f"💡 **API Efficiency:** Used {total_api_calls} API calls total (avg {avg_calls:.1f} per person). Saved approximately {api_efficiency:.0f}% of potential API calls through early stopping.")
    else:
        st.warning("⚠️ No valid email addresses were found for the provided data.")
        st.info(f"📊 **Processing Summary:** Processed {total_rows} rows using {total_api_calls} API calls (avg {total_api_calls/total_rows:.1f} per person)")

def render_smart_csv_upload_tab(api_key: str):
    """Optimized CSV upload with smart column detection."""
    
    st.subheader("📁 Smart CSV Upload & Column Detection")
    
    # Initialize session state
    if 'column_mapping' not in st.session_state:
        st.session_state['column_mapping'] = None
    if 'mapping_confirmed' not in st.session_state:
        st.session_state['mapping_confirmed'] = False
    if 'show_manual_selection' not in st.session_state:
        st.session_state['show_manual_selection'] = False
    if 'uploaded_df' not in st.session_state:
        st.session_state['uploaded_df'] = None
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=['csv', 'xlsx'],
        help="Upload any CSV or Excel file - our smart algorithm will detect the correct columns!"
    )
    
    if uploaded_file is not None:
        try:
            # Read file
            if uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            else:
                # Try different encodings for CSV
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                except UnicodeDecodeError:
                    try:
                        df = pd.read_csv(uploaded_file, encoding='latin-1')
                    except UnicodeDecodeError:
                        df = pd.read_csv(uploaded_file, encoding='cp1252')
            
            st.session_state['uploaded_df'] = df
            
            # Show basic file info
            st.subheader("📊 File Information")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Rows", len(df))
            with col2:
                st.metric("Total Columns", len(df.columns))
            with col3:
                st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")
            with col4:
                st.metric("Null Values", df.isnull().sum().sum())
            
            # Show column preview
            st.subheader("📋 Column Preview")
            preview_data = []
            for col in df.columns:
                sample_values = df[col].dropna().head(3).tolist()
                null_count = df[col].isnull().sum()
                null_percentage = (null_count / len(df)) * 100
                
                preview_data.append({
                    "Column Name": col,
                    "Data Type": str(df[col].dtype),
                    "Sample Values": ", ".join(map(str, sample_values)),
                    "Null Count": null_count,
                    "Null %": f"{null_percentage:.1f}%"
                })
            
            preview_df = pd.DataFrame(preview_data)
            st.dataframe(preview_df, use_container_width=True)
            
            # Reset mapping when new file is uploaded
            if st.session_state.get('last_file_name') != uploaded_file.name:
                st.session_state['column_mapping'] = None
                st.session_state['mapping_confirmed'] = False
                st.session_state['show_manual_selection'] = False
                st.session_state['last_file_name'] = uploaded_file.name
            
            # Smart column detection
            if not st.session_state['mapping_confirmed']:
                if not st.session_state.get('show_manual_selection', False):
                    # Run smart detection
                    with st.spinner("🔍 Analyzing columns and content..."):
                        detection_results = smart_column_detection(df)
                    
                    # Show confirmation dialog
                    render_column_confirmation_dialog(df, detection_results)
                else:
                    # Show manual selection
                    render_manual_column_selection(df)
            
            # Process data if mapping is confirmed
            if st.session_state['mapping_confirmed'] and st.session_state['column_mapping']:
                mapping = st.session_state['column_mapping']
                
                # Show confirmed mapping
                st.subheader("✅ Confirmed Column Mapping")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.success(f"**First Name:** `{mapping['firstname']}`")
                with col2:
                    st.success(f"**Last Name:** `{mapping['lastname']}`")
                with col3:
                    st.success(f"**Company URL:** `{mapping['companyURL']}`")
                with col4:
                    method_emoji = "🤖" if mapping['method'] == 'automatic' else "👤"
                    st.info(f"**Method:** {method_emoji} {mapping['method'].title()}")
                
                # Change mapping button
                if st.button("🔄 Change Column Mapping"):
                    st.session_state['mapping_confirmed'] = False
                    st.session_state['column_mapping'] = None
                    st.rerun()
                
                # Create cleaned dataset
                try:
                    # Map columns to standard names
                    cleaned_df = pd.DataFrame({
                        'firstname': df[mapping['firstname']],
                        'lastname': df[mapping['lastname']],
                        'companyURL': df[mapping['companyURL']]
                    })
                    
                    # Clean data
                    original_rows = len(cleaned_df)
                    cleaned_df = cleaned_df.dropna().copy()
                    cleaned_df = cleaned_df[
                        (cleaned_df['firstname'].astype(str).str.strip() != '') & 
                        (cleaned_df['lastname'].astype(str).str.strip() != '') & 
                        (cleaned_df['companyURL'].astype(str).str.strip() != '')
                    ]
                    
                    st.subheader("📊 Data Quality Analysis")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Original Rows", original_rows)
                    with col2:
                        st.metric("Valid Rows", len(cleaned_df))
                    with col3:
                        st.metric("Removed Rows", original_rows - len(cleaned_df))
                    with col4:
                        data_quality = (len(cleaned_df) / original_rows * 100) if original_rows > 0 else 0
                        st.metric("Data Quality", f"{data_quality:.1f}%")
                    
                    if len(cleaned_df) == 0:
                        st.error("❌ No valid rows found after cleaning. Please check your data quality.")
                        return
                    
                    # Show sample of cleaned data
                    st.subheader("📋 Cleaned Data Preview")
                    st.dataframe(cleaned_df.head(10), use_container_width=True)
                    
                    # Verification section
                    st.subheader("🚀 Email Verification")
                    
                    if st.button("Start Smart Verification", type="primary", key="smart_csv_verify"):
                        # Run the verification with the cleaned dataset
                        run_smart_verification(cleaned_df, api_key)
                
                except KeyError as e:
                    st.error(f"❌ Column mapping error: {str(e)}")
                    st.session_state['mapping_confirmed'] = False
                except Exception as e:
                    st.error(f"❌ Data processing error: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")
            st.info("💡 Try saving your file in UTF-8 encoding or as a different format.")

def render_single_entry_tab(api_key: str):
    """Renders the single entry verification tab content with improved algorithm."""
    st.subheader("👤 Single Email Verification")
    
    # Create a form container
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
        
        if result and result.get('email'):
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
                efficiency = ((result.get('total_formats_available', 1) - result.get('found_on_attempt', 1)) / result.get('total_formats_available', 1)) * 100
                st.metric("API Calls Saved", f"{efficiency:.0f}%")
            
            # Show tested formats (only the ones actually tested)
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
                'found_on_attempt': result.get('found_on_attempt'),
                'api_calls_saved': result.get('total_formats_available', 0) - result.get('found_on_attempt', 0)
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
    # Header
    st.markdown('<h1 class="main-header">📧 Email Verifier Pro</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Professional email verification with smart column detection</p>', unsafe_allow_html=True)
    
    # Sidebar for API key
    with st.sidebar:
        st.header("🔑 Configuration")
        api_key = st.text_input(
            "Enter your Reoon API Key",
            type="password",
            help="Get your API key from https://emailverifier.reoon.com/"
        )
        
        st.markdown("---")
        st.subheader("🤖 Smart Features")
        st.markdown("""
        **New in this version:**
        - 🔍 **Smart Column Detection** - Automatically detects firstname, lastname, and URL columns
        - 📊 **Content Analysis** - Analyzes data types and patterns
        - ✅ **Confirmation Dialog** - Review and confirm detected columns
        - 🔧 **Manual Override** - Choose columns manually if needed
        - ⚡ **Early Stopping** - Stops when valid email found (saves API calls)
        """)
        
        st.markdown("---")
        st.subheader("📋 Supported Column Names")
        st.markdown("""
        **First Name:** firstname, fname, first, given, prenom, nome, vorname
        
        **Last Name:** lastname, lname, last, surname, family, nom, apellido
        
        **Company URL:** url, website, site, domain, company_url, web, link
        """)
        
        st.markdown("---")
        st.subheader("🎯 Algorithm Features")
        st.markdown("""
        - Tests 14+ email format patterns
        - Stops immediately when valid email found
        - Tracks API efficiency metrics
        - Handles messy/inconsistent data
        - Multi-language column support
        """)
    
    # Main content area
    if not api_key:
        st.warning("⚠️ Please enter your API key in the sidebar to continue.")
        return
    
    # Tab structure (removed LinkedIn tab)
    tab1, tab2 = st.tabs(["🤖 Smart CSV Upload", "👤 Single Entry"])
    
    with tab1:
        render_smart_csv_upload_tab(api_key)
    
    with tab2:
        render_single_entry_tab(api_key)

if __name__ == "__main__":
    main()