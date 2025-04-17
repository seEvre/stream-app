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

# Function to add a random transparent pixel
def add_random_transparent_pixel(image_bytes: bytes) -> bytes:
    """Adds a random transparent pixel to the image."""
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGBA")
        pixels = img.load()
        x = random.randint(0, img.size[0] - 1)
        y = random.randint(0, img.size[1] - 1)
        pixels[x, y] = (0, 0, 0, 0)  # Make pixel transparent
        
        new_image_bytes = BytesIO()
        img.save(new_image_bytes, format="PNG")
        return new_image_bytes.getvalue()
    except Exception as e:
        logger.error(f"Error adding transparent pixel: {e}")
        return image_bytes  # Return original if fails

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
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh; /* Ensure full viewport height */
            margin: 0;
            padding: 0;
        }
        /* Main container */
        .main-container {
            width: 80%;
            max-width: 900px;
            padding: 20px;
            border-radius: 10px;
            background-color: #fff;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        /* Header */
        .header {
            background-color: #3498db;
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
        /* Input */
        .stTextInput>label, .stTextArea>label {
            color: #3498db;
            font-weight: bold;
        }
        /* Progress Bar */
        .stProgress>div>div {
            background-color: #3498db !important;
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
            color: #3498db;
            background-color: #cce5ff;
            border: 1px solid #b8daff;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }
        /* Drag and Drop Area */
        .drag-and-drop-area {
            border: 2px dashed #3498db;
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
            background-color: #3498db;
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
        /* Container Styling */
        .page-container {
            padding: 20px;
            border-radius: 10px;
            background-color: #fff;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
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
        logger.error(f"Error getting user info.")
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

        asset_id = response.json().get('assetId')  # Get the asset ID from the response
        return {"success": True, "asset_id": asset_id, "response": response.json()}  # Return the asset ID

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
if 'accounts' not in st.session_state:
    st.session_state.accounts = []
if 'selected_account' not in st.session_state:
    st.session_state.selected_account = None
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
if 'num_api_keys' not in st.session_state:
     st.session_state.num_api_keys = 1 # Default to 1 API key
if 'random_names' not in st.session_state:
    st.session_state.random_names = True #Random Names!
if 'add_transparent_pixel' not in st.session_state:
    st.session_state.add_transparent_pixel = True

# ---- Page Functions ----
def show_account_management_page():
    st.markdown('<div class="header"><h1>Account Management</h1><p>Add and manage your Roblox accounts.</p></div>', unsafe_allow_html=True)

    new_account_name = st.text_input("Account Name")
    new_api_key_method = st.radio("API Key Source", ["Enter Existing Key", "Generate from Cookie"], horizontal=True)

    new_api_key = None
    new_cookie = None

    if new_api_key_method == "Enter Existing Key":
        new_api_key = st.text_input("Roblox API Key", type="")
    else:
        new_cookie = st.text_area(".ROBLOSECURITY Cookie")

    if st.button("Add Account"):
        if new_account_name and (new_api_key or new_cookie):
            account = {"name": new_account_name, "api_key": new_api_key, "cookie": new_cookie, 'api_keys': []}
            st.session_state.accounts.append(account)
            st.success(f"Account '{new_account_name}' added successfully!")
        else:
            st.error("Please provide both an account name and either an API key or a cookie.")
    
    st.subheader("Account API Key Settings")
    
    num_api_keys = st.number_input("Number of API Keys", min_value=1, max_value=5, value=st.session_state.num_api_keys, step=1, help="The amount of keys created for an account. Do not overload.")
    st.session_state.num_api_keys = num_api_keys

    st.subheader("Existing Accounts")
    if st.session_state.accounts:
        for i, account in enumerate(st.session_state.accounts):
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**{account['name']}**")
                    # Display API key or Cookie status, not the value
                    st.write(f"API Key: {'Present' if account['api_key'] else 'Not Set'}")
                    st.write(f"Cookie: {'Present' if account['cookie'] else 'Not Set'}")
                with col2:
                    select_account_button = st.button(f"Select Account", key=f"select_account_{i}")
                    if select_account_button:
                        st.session_state.selected_account = account
                        st.success(f"Account '{account['name']}' selected!")
                with col3:
                    delete_account_button = st.button(f"Delete Account", key=f"delete_account_{i}")
                    if delete_account_button:
                        del st.session_state.accounts[i]
                        st.warning(f"Account '{account['name']}' deleted.")
                        break  # Prevent index out of bounds error after deletion
    else:
        st.info("No accounts added yet.")

    next_page_button = st.button("Next: Upload Settings")
    if next_page_button and st.session_state.accounts:
        st.session_state.page = 2
    elif not st.session_state.accounts:
        st.warning("Please add at least one account before proceeding.")

def show_upload_settings_page():
    st.markdown('<div class="header"><h1>Upload Settings</h1><p>Configure how your decals will be uploaded.</p></div>', unsafe_allow_html=True)

    # Ensure an account is selected
    if not st.session_state.selected_account:
        st.error("Please select an account first.")
        st.session_state.page = 1
        st.experimental_rerun()

    account = st.session_state.selected_account
    with st.container():
        st.markdown(f"Uploading with account: **{account['name']}**")

        col1, col2 = st.columns(2)
        
        with col1:
            upload_option = st.radio("Image Source", ["Upload Image Files", "Provide Image URLs"])
            st.session_state.image_type = st.selectbox("Image Type", ["image/png", "image/jpeg"])
            st.session_state.add_transparent_pixel = st.checkbox("Add Random Pixel", value=True, help="Adds a random pixel to prevent deletion of the decal")

        with col2:
            st.session_state.random_names = st.checkbox("Use Random Names", value=True, help="Creates random names for the assets")
            st.session_state.naming_option = st.radio("Naming Method", ["Use Filenames", "Custom Naming Pattern", "Custom Names List"])
    
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
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col3:
            next_page_button = st.button("Next: Metadata Settings")
            if next_page_button:
                st.session_state.page = 3

def show_metadata_settings_page():
    st.markdown('<div class="header"><h1>Metadata Settings</h1><p>Configure the metadata for your decals.</p></div>', unsafe_allow_html=True)

    if not st.session_state.selected_account:
        st.error("Please select an account first.")
        st.session_state.page = 1
        st.experimental_rerun()

    with st.container():
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

        col1, col2, col3 = st.columns([1, 1, 1])
        with col3:
            next_page_button = st.button("Next: Start Upload")
            if next_page_button:
                st.session_state.page = 4

def show_upload_page():
    st.markdown('<div class="header"><h1>Start Upload</h1><p>Start the decal upload process.</p></div>', unsafe_allow_html=True)

    if not st.session_state.selected_account:
        st.error("Please select an account first.")
        st.session_state.page = 1
        st.experimental_rerun()

    account = st.session_state.selected_account
    st.markdown(f"Number of API Keys:{st.session_state.num_api_keys}")
    if st.button("Start Upload"):
        if not account['api_key'] and not account['cookie']:
            st.error("Please provide a valid API key or cookie for the selected account.")
        else:
            api_keys = []
            
            # Use the stored API keys if available.
            if account.get('api_keys'):
                api_keys = account['api_keys']

            # Otherwise derive new keys
            if len(api_keys) < st.session_state.num_api_keys and account['cookie']:
                for number in range(st.session_state.num_api_keys):
                    # Attempt to generate API key from cookie, though it is better to move this to the account creation
                    api_key_to_use = create_api_key(account['cookie'])
                    if api_key_to_use:
                        api_keys.append(api_key_to_use)
            
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

                        if st.session_state.add_transparent_pixel:
                            image_bytes = add_random_transparent_pixel(image_bytes)

                        if st.session_state.random_names:
                            name = " ".join(random.choices(CLEAN_WORDS, k=3))
                        elif st.session_state.naming_option == "Use Filenames":
                            name = os.path.splitext(file_name)[0]
                        elif st.session_state.naming_option == "Custom Naming Pattern":
                            name = st.session_state.name_pattern.replace("{index}", str(i + 1))
                        else:  # Custom Names List
                            name = names_list[i] if i < len(names_list) else f"Decal {i + 1}"

                        api_key_to_use = api_keys[i % len(api_keys)]
                        user_id_to_use = account.get('user_id', "")  # Provide user_id if stored

                        # Attempt to derive User ID if one does not exist
                        if not user_id_to_use and account['cookie']:
                            user_information = get_user_info(account['cookie'])
                            # Attempt to derive user id with get user information
                            if user_information is not None:
                                user_id_to_use = user_information['id']
                            else:
                                # If the cookie for some reason doesnt work skip the item
                                raise ValueError("Cookie Invalid")

                        # Call the updated upload_decal function
                        result = upload_decal(api_key_to_use, image_bytes, name, st.session_state.description, user_id_to_use, st.session_state.image_type)
                        result["file"] = file_name
                        st.session_state.results.append(result)

                        if st.session_state.add_delay and i < len(files_to_process) - 1:
                            time.sleep(st.session_state.delay_seconds)

                    except requests.exceptions.RequestException as e:
                        error_message = f"Error processing {file_item}: {e}"
                        logger.error(error_message)
                        st.session_state.results.append({"file": file_item, "success": False, "error": error_message})
                        continue
                    except ValueError as e:
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

                    # Add a direct link to the asset on Roblox
                    def make_clickable(asset_id):
                        if asset_id:
                            return f'<a target="_blank" href="https://www.roblox.com/library/{asset_id}">View on Roblox</a>'
                        else:
                            return ''

                    results_df['Asset Link'] = results_df.get('asset_id','').apply(make_clickable)
                    st.write(results_df.to_html(escape=False, render_links=True), unsafe_allow_html=True)

                    # 40. CSV Download Button
                    csv = results_df.to_csv(index=False)
                    st.download_button(
                        label="Download Results as CSV",
                        data=csv,
                        file_name="roblox_upload_results.csv",
                        mime="text/csv",
                    )

# ---- Main App Flow ----
st.markdown("""
    <style>
    .main {
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <style>
        /* General */
        .stRadio > label {
            font-size: large;
        }
        /* Centralize the page content */
        body > div.reportview-container > div > div {
            width: 80%;
            max-width: 900px;
            margin: 0 auto;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    label {
        font-size: large;
    }
    h1 {
        font-size: 2.5rem;
    }
    h2 {
        font-size: 2rem;
    }
    [data-testid="stForm"] {
        border: 0px
    }
    </style>
    """, unsafe_allow_html=True)

with st.container():
    with st.container():
        if st.session_state.page == 1:
            show_account_management_page()
        elif st.session_state.page == 2:
            show_upload_settings_page()
        elif st.session_state.page == 3:
            show_metadata_settings_page()
        elif st.session_state.page == 4:
            show_upload_page()

        # App Note in Footer
        st.markdown("---")
        st.markdown("**Note:** This tool uses the Roblox API. Ensure compliance with Roblox's Terms of Service when uploading content.")
