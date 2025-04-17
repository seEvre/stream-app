import streamlit as st
import requests
import json
import random
import logging
import pandas as pd
import time
import os
from io import BytesIO
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of clean words for random API key naming
CLEAN_WORDS = ["sky", "blue", "cloud", "star", "moon", "sun", "rainbow", "tree", 
               "flower", "river", "mountain", "ocean", "forest", "meadow", "bird", 
               "dolphin", "panda", "robot", "rocket", "planet", "galaxy", "comet"]

# Function to get CSRF token from cookie
def get_csrf_token(cookie):
    headers = {"Cookie": f".ROBLOSECURITY={cookie}"}
    response = requests.post("https://auth.roblox.com/v2/logout", headers=headers)
    if response.status_code == 403:
        xsrf_token = response.headers.get("x-csrf-token")
        if xsrf_token:
            return xsrf_token
    raise Exception("Failed to get CSRF token")

# Function to get user info from cookie
def get_user_info(cookie):
    headers = {"Cookie": f".ROBLOSECURITY={cookie}"}
    response = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

# Function to create API key from cookie
def create_api_key(cookie):
    try:
        logger.info("Starting API key creation...")
        xsrf_token = get_csrf_token(cookie)
        logger.info(f"CSRF Token: {xsrf_token}")
    except Exception as e:
        logger.error(f"Error getting CSRF token: {e}")
        return None

    user_info = get_user_info(cookie)
    if user_info is None:
        logger.error("Failed to get user info.")
        return None
    logger.info(f"User Info: {user_info}")

    api_name = " ".join(random.choices(CLEAN_WORDS, k=3))
    api_description = " ".join(random.choices(CLEAN_WORDS, k=5))

    payload = {
        "cloudAuthUserConfiguredProperties": {
            "name": api_name,
            "description": api_description,
            "isEnabled": True,
            "allowedCidrs": ["0.0.0.0/0"],
            "scopes": [{"scopeType": "asset", "targetParts": ["U"], "operations": ["read", "write"]}],
        }
    }
    headers = {"Cookie": f".ROBLOSECURITY={cookie}", "Content-Type": "application/json", "X-CSRF-TOKEN": xsrf_token}
    url = "https://apis.roblox.com/cloud-authentication/v1/apiKey"
    res = requests.post(url, json=payload, headers=headers)
    logger.info(f"API Key Response: {res.status_code} - {res.text}")
    if res.status_code == 200:
        try:
            api_key_info = res.json()
            return api_key_info.get("apikeySecret")
        except json.JSONDecodeError:
            logger.exception("Error decoding JSON response.")
            return None
    else:
        logger.error(f"Error creating API key: {res.status_code} - {res.text}")
        return None

# Function to upload a single decal
def upload_decal(api_key, image_bytes, name, description=""):
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    # First create the payload with metadata
    create_payload = {
        "name": name,
        "description": description,
        "assetType": "Decal"  # Assuming this is the correct asset type for decals
    }
    
    # Request to create asset
    create_url = "https://apis.roblox.com/assets/v1/assets"
    create_response = requests.post(create_url, headers=headers, json=create_payload)
    
    if create_response.status_code != 200:
        return {"success": False, "error": f"Failed to create asset: {create_response.text}"}
    
    create_data = create_response.json()
    asset_id = create_data.get("assetId")
    operation_id = create_data.get("operationId")
    
    # Now upload the actual image
    upload_url = f"https://apis.roblox.com/assets/v1/assets/{asset_id}/contents"
    upload_headers = {
        "x-api-key": api_key,
        "Content-Type": "application/octet-stream"
    }
    
    upload_response = requests.post(upload_url, headers=upload_headers, data=image_bytes)
    
    if upload_response.status_code != 200:
        return {"success": False, "error": f"Failed to upload image: {upload_response.text}"}
    
    # Check asset status
    status_url = f"https://apis.roblox.com/assets/v1/operations/{operation_id}"
    status_response = requests.get(status_url, headers=headers)
    
    return {
        "success": True,
        "asset_id": asset_id,
        "operation_id": operation_id,
        "status": status_response.json() if status_response.status_code == 200 else "Unknown"
    }

# Streamlit App
st.set_page_config(page_title="Roblox Decal Uploader", page_icon="🎮", layout="wide")

st.title("Roblox Decal Mass Uploader")
st.markdown("Upload multiple decals to Roblox using the Roblox API")

# Sidebar for API key configuration
st.sidebar.header("API Configuration")
api_key_method = st.sidebar.radio("API Key Method", ["Enter API Key", "Generate from Cookie"])

api_key = None

if api_key_method == "Enter API Key":
    api_key = st.sidebar.text_input("Enter your Roblox API Key")
else:
    # Use standard text_area without type parameter
    st.sidebar.markdown("**Enter your .ROBLOSECURITY cookie (sensitive data)**")
    cookie = st.sidebar.text_area("Cookie value will be hidden when typing", height=100)
    if st.sidebar.button("Generate API Key"):
        with st.sidebar.spinner("Generating API Key..."):
            api_key = create_api_key(cookie)
            if api_key:
                st.sidebar.success("API Key generated successfully!")
                # Display in a way that can be copied but not immediately visible
                st.sidebar.markdown("**Your API Key (click to reveal):**")
                expander = st.sidebar.expander("Show API Key")
                with expander:
                    st.code(api_key)
            else:
                st.sidebar.error("Failed to generate API Key. Check logs for details.")

# Main upload section
st.header("Upload Decals")

upload_option = st.radio("Upload Method", ["Upload Images", "Provide Image URLs"])

if upload_option == "Upload Images":
    uploaded_files = st.file_uploader("Upload image files", accept_multiple_files=True, type=["png", "jpg", "jpeg"])
    
    if uploaded_files:
        st.write(f"Uploaded {len(uploaded_files)} images")
        
        # Display a preview of the images in a grid
        cols = st.columns(4)
        for i, file in enumerate(uploaded_files[:8]):  # Show first 8 images
            with cols[i % 4]:
                img = Image.open(file)
                st.image(img, caption=file.name, width=150)
        
        if len(uploaded_files) > 8:
            st.write(f"... and {len(uploaded_files) - 8} more")
else:
    image_urls = st.text_area("Enter image URLs (one per line)")
    preview_button = st.button("Preview URLs")
    
    if preview_button and image_urls:
        urls = [url.strip() for url in image_urls.split("\n") if url.strip()]
        st.write(f"Found {len(urls)} URLs")
        
        # Preview first few images
        cols = st.columns(4)
        preview_count = 0
        
        for i, url in enumerate(urls[:8]):
            try:
                response = requests.get(url)
                img = Image.open(BytesIO(response.content))
                with cols[i % 4]:
                    st.image(img, caption=f"URL {i+1}", width=150)
                preview_count += 1
            except Exception as e:
                st.error(f"Could not preview URL {i+1}: {e}")
        
        if len(urls) > 8:
            st.write(f"... and {len(urls) - 8} more")

# Additional upload options
st.header("Upload Settings")

col1, col2 = st.columns(2)
with col1:
    naming_option = st.radio("Naming Method", ["Use Filenames", "Custom Naming Pattern", "Custom Names List"])
    
    if naming_option == "Custom Naming Pattern":
        name_pattern = st.text_input("Name Pattern (use {index} for numbering)", "My Decal {index}")
    elif naming_option == "Custom Names List":
        custom_names = st.text_area("Enter custom names (one per line)")

with col2:
    description = st.text_area("Default Description (optional)")
    add_delay = st.checkbox("Add delay between uploads", value=True)
    if add_delay:
        delay_seconds = st.slider("Delay in seconds", 1, 10, 3)

# Upload button
if st.button("Start Upload"):
    if not api_key:
        st.error("Please provide a valid API key first.")
    else:
        # Initialize progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        
        results = []
        
        # Determine the list of files/URLs to process
        files_to_process = []
        
        if upload_option == "Upload Images" and uploaded_files:
            files_to_process = uploaded_files
        elif upload_option == "Provide Image URLs" and image_urls:
            urls = [url.strip() for url in image_urls.split("\n") if url.strip()]
            files_to_process = urls
        
        if not files_to_process:
            st.warning("No files or URLs to process.")
        else:
            # Get names list if using custom names
            names_list = []
            if naming_option == "Custom Names List" and custom_names:
                names_list = [name.strip() for name in custom_names.split("\n") if name.strip()]
                if len(names_list) < len(files_to_process):
                    st.warning(f"Warning: Only {len(names_list)} names provided for {len(files_to_process)} files. Some files will use default naming.")
            
            # Process each file
            for i, file_item in enumerate(files_to_process):
                # Update progress
                progress = (i + 1) / len(files_to_process)
                progress_bar.progress(progress)
                status_text.text(f"Processing item {i+1} of {len(files_to_process)}")
                
                # Get image bytes
                if upload_option == "Upload Images":
                    file_name = file_item.name
                    image_bytes = file_item.getvalue()
                else:  # URL mode
                    try:
                        response = requests.get(file_item)
                        image_bytes = response.content
                        file_name = file_item.split("/")[-1]
                    except Exception as e:
                        results.append({
                            "file": file_item,
                            "success": False,
                            "error": str(e)
                        })
                        continue
                
                # Determine name
                if naming_option == "Use Filenames":
                    name = os.path.splitext(file_name)[0]
                elif naming_option == "Custom Naming Pattern":
                    name = name_pattern.replace("{index}", str(i+1))
                else:  # Custom Names List
                    name = names_list[i] if i < len(names_list) else f"Decal {i+1}"
                
                # Upload decal
                result = upload_decal(api_key, image_bytes, name, description)
                result["file"] = file_name
                results.append(result)
                
                # Add delay if configured
                if add_delay and i < len(files_to_process) - 1:
                    time.sleep(delay_seconds)
            
            # Display results
            with results_container:
                st.subheader("Upload Results")
                
                # Success/failure summary
                success_count = sum(1 for r in results if r.get("success", False))
                st.write(f"Uploaded {success_count} of {len(results)} items successfully.")
                
                # Detailed results as a dataframe
                results_df = pd.DataFrame(results)
                st.dataframe(results_df)
                
                # Download results as CSV
                csv = results_df.to_csv(index=False)
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name="roblox_upload_results.csv",
                    mime="text/csv",
                )

# Footer
st.markdown("---")
st.markdown("**Note:** This tool uses the Roblox API. Make sure you comply with Roblox's Terms of Service when uploading content.")
