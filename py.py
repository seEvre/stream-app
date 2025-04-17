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
from typing import List, Dict, Union
import base64

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
CLEAN_WORDS = ["sky", "blue", "cloud", "star", "moon", "sun", "rainbow", "tree",
               "flower", "river", "mountain", "ocean", "forest", "meadow", "bird",
               "dolphin", "panda", "robot", "rocket", "planet", "galaxy", "comet"]
ROBLOX_ASSETS_API = "https://apis.roblox.com/assets/v1/assets"
ROBLOX_CLOUD_AUTH_API = "https://apis.roblox.com/cloud-authentication/v1/apiKey"

# Function to encode image to base64
def encode_image(image_bytes: bytes) -> str:
    """Encodes image bytes to base64 string for HTML display."""
    return base64.b64encode(image_bytes).decode('utf-8')

# Custom Theme (Improved)
st.set_page_config(page_title="Roblox Decal Uploader", page_icon="🎮", layout="wide")

# Enhanced Styling with Markdown/CSS (More Comprehensive)
st.markdown("""
    <style>
        /* General */
        body {
            font-family: 'Arial', sans-serif;
            background-color: #f8f9fa;
            color: #343a40;
        }
        /* Header */
        .header {
            background-color: #007bff;
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header p {
            font-size: 1.1em;
            color: #d1ecf1;
        }
        /* Sidebar */
        /*.sidebar .stButton>button {
            width: 100%;
            margin-bottom: 15px;
            background-color: #28a745;
            border-color: #28a745;
            color: white;
            transition: background-color 0.3s;
        }
        .sidebar .stButton>button:hover {
            background-color: #218838;
        }
        .sidebar .stRadio>label {
            color: #007bff;
            font-weight: bold;
        }*/
        /* Input */
        .stTextInput>label, .stTextArea>label {
            color: #007bff;
            font-weight: bold;
        }
        /* Progress Bar */
        .stProgress>div>div {
            background-color: #007bff !important;
        }
        /* Alert Messages */
        .success-message {
            color: #28a745;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }
        .error-message {
            color: #dc3545;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }
        .info-message {
            color: #007bff;
            background-color: #cce5ff;
            border: 1px solid #b8daff;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }
        /* Drag and Drop Area */
        .drag-and-drop-area {
            border: 2px dashed #007bff;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
            cursor: pointer;
            margin-bottom: 20px;
            transition: border-color 0.3s;
        }
        .drag-and-drop-area:hover {
            border-color: #0056b3;
        }
        /* Image Preview */
        .image-preview {
            max-width: 150px;
            margin: 5px;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-shadow: 0 0 5px rgba(0,0,0,0.2);
            transition: transform 0.2s;
        }
        .image-preview:hover {
            transform: scale(1.1);
        }
        /* Custom Button */
        .custom-button {
            background-color: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s, transform 0.2s;
        }
        .custom-button:hover {
            background-color: #0056b3;
            transform: scale(1.05);
        }
        /* Next Button */
        .next-button {
            background-color: #28a745;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
            margin-top: 20px;
        }
        .next-button:hover {
            background-color: #218838;
        }
    </style>
""", unsafe_allow_html=True)

# ---- Helper Functions ----
def get_csrf_token(cookie: str) -> str:
    headers = {"Cookie": f".ROBLOSECURITY={cookie}"}
    response = requests.post("https://auth.roblox.com/v2/logout", headers=headers)
    if response.status_code == 403:
        xsrf_token = response.headers.get("x-csrf-token")
        if xsrf_token:
            return xsrf_token
    raise Exception("Failed to get CSRF token")

def get_user_info(cookie: str) -> Union[Dict, None]:
    headers = {"Cookie": f".ROBLOSECURITY={cookie}"}
    response = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

def create_api_key(cookie: str) -> Union[str, None]:
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
    try:
        res = requests.post(ROBLOX_CLOUD_AUTH_API, json=payload, headers=headers)
        logger.info(f"API Key Response: {res.status_code} - {res.text}")
        res.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        api_key_info = res.json()
        return api_key_info.get("apikeySecret")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        st.error(f"API Key creation failed: {e}")
        return None
    except json.JSONDecodeError:
        logger.exception("Error decoding JSON response.")
        st.error("Failed to decode API response.")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        st.error("An unexpected error occurred. See logs for details.")
        return None

def upload_decal(api_key: str, image_bytes: bytes, name: str, description: str, user_id: str, image_type: str = "image/png") -> Dict:
    headers = {
        "x-api-key": api_key
    }

    files = {
        'request': (None, json.dumps({
            "assetType": "Decal",
            "displayName": name,
            "description": description,
            "creationContext": {
                "creator": {
                    "userId": user_id
                }
            }
        })),
        'fileContent': (f'{name}.png', image_bytes, image_type)  # or 'image/jpeg'
    }

    try:
        response = requests.post(ROBLOX_ASSETS_API, headers=headers, files=files)
        response.raise_for_status()

        return {"success": True, "response": response.json()}

    except requests.exceptions.RequestException as e:
        error_message = f"Request failed: {e} - {response.text if 'response' in locals() else 'No response'}"
        logger.error(error_message)
        return {"success": False, "error": error_message}

    except json.JSONDecodeError:
        error_message = "Failed to decode API response."
        logger.exception(error_message)
        return {"success": False, "error": error_message}

    except Exception as e:
        error_message = f"Unexpected error occurred: {e}"
        logger.exception(error_message)
        return {"success": False, "error": error_message}

# ---- Initialize Session State ----
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'api_key' not in st.session_state:
    st.session_state.api_key = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = ""
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'image_type' not in st.session_state:
    st.session_state.image_type = "image/png"
if 'naming_option' not in st.session_state:
    st.session_state.naming_option = "Use Filenames"
if 'name_pattern' not in st.session_state:
    st.session_state.name_pattern = "My Decal {index}"
if 'custom_names' not in st.session_state:
    st.session_state.custom_names = ""
if 'description' not in st.session_state:
    st.session_state.description = ""
if 'add_delay' not in st.session_state:
    st.session_state.add_delay = False
if 'delay_seconds' not in st.session_state:
    st.session_state.delay_seconds = 3
if 'results' not in st.session_state:
    st.session_state.results = []

# ---- Page Functions ----
def show_api_authentication_page():
    st.markdown('<div class="header"><h1>API Authentication</h1><p>Enter your API key or generate one using your Roblox cookie.</p></div>', unsafe_allow_html=True)

    api_key_method = st.radio("API Key Source", ["Enter Existing Key", "Generate from Cookie"])

    if api_key_method == "Enter Existing Key":
        st.session_state.api_key = st.text_input("Enter your Roblox API Key", type="password")
        if st.session_state.api_key:
            st.markdown('<p class="success-message">API Key entered successfully!</p>', unsafe_allow_html=True)
    else:
        st.markdown("**Enter your .ROBLOSECURITY cookie (sensitive data)**")
        cookie = st.text_area("Cookie value will be hidden when typing", height=100)
        if st.button("Generate API Key from Cookie"):
            with st.spinner("Generating API Key..."):
                st.session_state.api_key = create_api_key(cookie)
                if st.session_state.api_key:
                    st.markdown('<p class="success-message">API Key generated successfully!</p>', unsafe_allow_html=True)
                    expander = st.expander("Show API Key")
                    with expander:
                        st.code(st.session_state.api_key)
                else:
                    st.markdown('<p class="error-message">Failed to generate API Key. Check logs for details.</p>', unsafe_allow_html=True)

    if st.session_state.api_key:
        next_page_button = st.markdown('<button class="next-button">Next: Upload Settings</button>', unsafe_allow_html=True)
        if next_page_button:
            st.session_state.page = 2

def show_upload_settings_page():
    st.markdown('<div class="header"><h1>Upload Settings</h1><p>Configure how your decals will be uploaded.</p></div>', unsafe_allow_html=True)

    st.session_state.user_id = st.text_input("Enter User ID", value=st.session_state.user_id, help="The user ID to associate with the uploaded decals.")
    upload_option = st.radio("Image Source", ["Upload Image Files", "Provide Image URLs"])
    st.session_state.image_type = st.selectbox("Image Type", ["image/png", "image/jpeg"])

    st.markdown('<div class="drag-and-drop-area">Drag and drop your image files here</div>', unsafe_allow_html=True)

    if upload_option == "Upload Image Files":
        st.session_state.uploaded_files = st.file_uploader("Upload image files", accept_multiple_files=True, type=["png", "jpg", "jpeg"])

        if st.session_state.uploaded_files:
            st.success(f"Uploaded {len(st.session_state.uploaded_files)} images")
            cols = st.columns(4)
            for i, file in enumerate(st.session_state.uploaded_files[:8]):
                with cols[i % 4]:
                    image_bytes = file.getvalue()
                    image_data = encode_image(image_bytes)
                    st.markdown(f'<img src="data:image/png;base64,{image_data}" class="image-preview">', unsafe_allow_html=True)
            if len(st.session_state.uploaded_files) > 8:
                st.info(f"... and {len(st.session_state.uploaded_files) - 8} more")
    else:
        st.session_state.uploaded_files = []

    next_page_button = st.markdown('<button class="next-button">Next: Metadata Settings</button>', unsafe_allow_html=True)
    if next_page_button:
        st.session_state.page = 3

def show_metadata_settings_page():
    st.markdown('<div class="header"><h1>Metadata Settings</h1><p>Configure the metadata for your decals.</p></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.naming_option = st.radio("Naming Method", ["Use Filenames", "Custom Naming Pattern", "Custom Names List"])

        if st.session_state.naming_option == "Custom Naming Pattern":
            st.session_state.name_pattern = st.text_input("Name Pattern (use {index} for numbering)", "My Decal {index}")
        elif st.session_state.naming_option == "Custom Names List":
            st.session_state.custom_names = st.text_area("Enter custom names (one per line)")

    with col2:
        st.session_state.description = st.text_area("Default Description (optional)")
        st.session_state.add_delay = st.checkbox("Add delay between uploads", value=True)
        if st.session_state.add_delay:
            st.session_state.delay_seconds = st.slider("Delay in seconds", 1, 10, 3)

    next_page_button = st.markdown('<button class="next-button">Next: Start Upload</button>', unsafe_allow_html=True)
    if next_page_button:
        st.session_state.page = 4

def show_upload_page():
    st.markdown('<div class="header"><h1>Start Upload</h1><p>Start the decal upload process.</p></div>', unsafe_allow_html=True)

    start_upload = st.markdown('<button class="custom-button">Start Upload</button>', unsafe_allow_html=True)
    if start_upload and st.button("Start Upload (Hidden)"):  # Keep the hidden button for logic
        if not st.session_state.api_key:
            st.error("Please provide a valid API key first.")
        elif not st.session_state.user_id:
            st.error("Please provide a User ID.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()

            st.session_state.results = []

            files_to_process = st.session_state.uploaded_files

            if not files_to_process:
                st.warning("No files or URLs to process.")
            else:
                names_list = []
                if st.session_state.naming_option == "Custom Names List":
                    names_list = [name.strip() for name in st.session_state.custom_names.split("\n")]
                    if len(names_list) < len(files_to_process):
                        st.warning(f"Warning: Only {len(names_list)} names provided for {len(files_to_process)} files. Some files will use default naming.")

                for i, file_item in enumerate(files_to_process):
                    progress = (i + 1) / len(files_to_process)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing item {i + 1} of {len(files_to_process)}")

                    try:
                        file_name = file_item.name
                        image_bytes = file_item.getvalue()

                        if st.session_state.naming_option == "Use Filenames":
                            name = os.path.splitext(file_name)[0]
                        elif st.session_state.naming_option == "Custom Naming Pattern":
                            name = st.session_state.name_pattern.replace("{index}", str(i + 1))
                        else:  # Custom Names List
                            name = names_list[i] if i < len(names_list) else f"Decal {i + 1}"

                        # Call the updated upload_decal function
                        result = upload_decal(st.session_state.api_key, image_bytes, name, st.session_state.description, st.session_state.user_id, st.session_state.image_type)
                        result["file"] = file_name

                        st.session_state.results.append(result)

                        if st.session_state.add_delay and i < len(files_to_process) - 1:
                            time.sleep(st.session_state.delay_seconds)

                    except requests.exceptions.RequestException as e:
                        error_message = f"Error processing {file_item}: {e}"
                        logger.error(error_message)
                        st.session_state.results.append({"file": file_item, "success": False, "error": error_message})
                        continue

                    except Exception as e:
                        error_message = f"Unexpected error processing {file_item}: {e}"
                        logger.error(error_message)
                        st.session_state.results.append({"file": file_item, "success": False, "error": error_message})
                        continue

                # Display Results
                with results_container:
                    st.subheader("Upload Results")

                    success_count = sum(1 for r in st.session_state.results if r.get("success", False))
                    st.markdown(f"Uploaded **{success_count}** of **{len(st.session_state.results)}** items successfully.")

                    # 39. Results as Dataframe
                    results_df = pd.DataFrame(st.session_state.results)
                    st.dataframe(results_df)

                    # 40. CSV Download Button
                    csv = results_df.to_csv(index=False)
                    st.download_button(
                        label="Download Results as CSV",
                        data=csv,
                        file_name="roblox_upload_results.csv",
                        mime="text/csv",
                    )

# ---- Main App Flow ----
if st.session_state.page == 1:
    show_api_authentication_page()
elif st.session_state.page == 2:
    show_upload_settings_page()
elif st.session_state.page == 3:
    show_metadata_settings_page()
elif st.session_state.page == 4:
    show_upload_page()

# App Note in Footer
st.markdown("---")
st.markdown("**Note:** This tool uses the Roblox API. Ensure compliance with Roblox's Terms of Service when uploading content.")
