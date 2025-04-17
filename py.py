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
import hashlib  # Import hashlib
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

# 1. Custom Theme (Improved)
st.set_page_config(page_title="Roblox Decal Uploader", page_icon="🎮", layout="wide")

# 2. Enhanced Styling with Markdown/CSS (More Comprehensive)
st.markdown("""
    <style>
        /* General */
        body {
            font-family: sans-serif;
            background-color: #f4f4f4;
            color: #333;
        }
        /* Header */
        .header {
            background-color: #3498db;
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
        }
        /* Sidebar */
        .sidebar .stButton>button {
            width: 100%;
            margin-bottom: 10px;
        }
        .sidebar .stRadio>label {
            color: #3498db;
        }
        /* Button */
        .stButton>button {
            color: #fff;
            background-color: #2ecc71;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        .stButton>button:hover {
            background-color: #27ae60;
        }
        /* Input */
        .stTextInput>label, .stTextArea>label {
            color: #3498db;
        }
        /* Progress Bar */
        .stProgress>div>div {
            background-color: #3498db !important;
        }
        /* Alert Messages */
        .success-message {
            color: green;
            margin-top: 10px;
        }
        .error-message {
            color: red;
            margin-top: 10px;
        }
        .info-message {
            color: #3498db;
            margin-top: 10px;
        }

        /* Drag and Drop Area */
        .drag-and-drop-area {
            border: 2px dashed #3498db;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
            cursor: pointer;
        }

        /* Image Preview */
        .image-preview {
            max-width: 150px;
            margin: 5px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Header Redesign
st.markdown('<div class="header"><h1>Roblox Decal Mass Uploader</h1><p>Effortlessly upload decals to Roblox.</p></div>', unsafe_allow_html=True)

# 4. Enhanced Sidebar with Progressive Disclosure
with st.sidebar:
    st.header("API & Authentication")

    api_key_method = st.radio("API Key Source", ["Enter Existing Key", "Generate from Cookie"])

    api_key = None

    if api_key_method == "Enter Existing Key":
        api_key = st.text_input("Enter your Roblox API Key", type="password")
        if api_key:
            st.markdown('<p class="success-message">API Key entered successfully!</p>', unsafe_allow_html=True)
    else:
        st.markdown("**Enter your .ROBLOSECURITY cookie (sensitive data)**")
        cookie = st.text_area("Cookie value will be hidden when typing", height=100)
        if st.button("Generate API Key from Cookie"):
            with st.spinner("Generating API Key..."):
                api_key = create_api_key(cookie)
                if api_key:
                    st.markdown('<p class="success-message">API Key generated successfully!</p>', unsafe_allow_html=True)
                    expander = st.expander("Show API Key")
                    with expander:
                        st.code(api_key)
                else:
                    st.markdown('<p class="error-message">Failed to generate API Key. Check logs for details.</p>', unsafe_allow_html=True)

    # Advanced Settings
    with st.expander("Advanced Settings"):
        st.markdown("## Rate Limiting")
        rate_limit = st.slider("Requests per second", 1, 10, 5)
        st.markdown("## Connection Pooling")
        max_connections = st.slider("Max connections", 10, 100, 50)
        st.markdown("## Caching")
        cache_duration = st.slider("Cache duration (seconds)", 0, 60, 30)

# 13. Improved Helper Functions
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
        error_message = f"An unexpected error occurred: {e}"
        logger.exception(error_message)
        return {"success": False, "error": error_message}

# 14. Main UI: Decal Upload Section
st.header("Decal Upload")

# Added userId input
user_id = st.text_input("Enter User ID", value="", help="The user ID to associate with the uploaded decals.")

# 15. Upload Method Selection
upload_option = st.radio("Image Source", ["Upload Image Files", "Provide Image URLs"])

# Add an image type selection
image_type = st.selectbox("Image Type", ["image/png", "image/jpeg"])

# 21. Drag and Drop Area
st.markdown('<div class="drag-and-drop-area">Drag and drop your image files here</div>', unsafe_allow_html=True)

if upload_option == "Upload Image Files":
    # 16. Multiple File Uploader
    uploaded_files = st.file_uploader("Upload image files", accept_multiple_files=True, type=["png", "jpg", "jpeg"])

    if uploaded_files:
        # 17. Dynamic Number of Uploaded Files Message
        st.success(f"Uploaded {len(uploaded_files)} images")

        # 18. Image Preview Grid with Limited Display
        cols = st.columns(4)
        for i, file in enumerate(uploaded_files[:8]):  # Show first 8 images
            with cols[i % 4]:
                # Display image with base64 encoding
                image_bytes = file.getvalue()
                image_data = encode_image(image_bytes)
                st.markdown(f'<img src="data:image/png;base64,{image_data}" class="image-preview">', unsafe_allow_html=True)

        # 19. Info Message for More Files
        if len(uploaded_files) > 8:
            st.info(f"... and {len(uploaded_files) - 8} more")


else:
    # 20. Image URL Input Field
    image_urls = st.text_area("Enter image URLs (one per line)")
    # 21. Preview URLs Button
    preview_button = st.button("Preview URLs")

    if preview_button and image_urls:
        # 22. URL Parsing
        urls = [url.strip() for url in image_urls.split("\n") if url.strip()]
        # 23. Number of URLs Message
        st.success(f"Found {len(urls)} URLs")

        # 24. Preview URLs in a Grid
        cols = st.columns(4)
        for i, url in enumerate(urls[:8]):
            try:
                response = requests.get(url)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content))
                with cols[i % 4]:
                    image_bytes = BytesIO()
                    img.save(image_bytes, format="PNG")
                    image_data = encode_image(image_bytes.getvalue())
                    st.markdown(f'<img src="data:image/png;base64,{image_data}" class="image-preview">', unsafe_allow_html=True)
            except requests.exceptions.RequestException as e:
                st.error(f"Could not preview URL {i + 1}: {e}")

        if len(urls) > 8:
            st.info(f"... and {len(urls) - 8} more")

# 25. Upload Settings Section
st.header("Upload Settings")

col1, col2 = st.columns(2)
with col1:
    # 26. Naming Method Radio Buttons
    naming_option = st.radio("Naming Method", ["Use Filenames", "Custom Naming Pattern", "Custom Names List"])

    if naming_option == "Custom Naming Pattern":
        # 27. Custom Naming Pattern Input
        name_pattern = st.text_input("Name Pattern (use {index} for numbering)", "My Decal {index}")
    elif naming_option == "Custom Names List":
        # 28. Custom Names Text Area
        custom_names = st.text_area("Enter custom names (one per line)")

with col2:
    # 29. Default Description Input
    description = st.text_area("Default Description (optional)")
    # 30. Add Delay Checkbox
    add_delay = st.checkbox("Add delay between uploads", value=True)
    if add_delay:
        # 31. Delay Slider
        delay_seconds = st.slider("Delay in seconds", 1, 10, 3)

# 32. Start Upload Button
if st.button("Start Upload"):
    if not api_key:
        # 33. No API Key Error Message
        st.error("Please provide a valid API key first.")
    elif not user_id:
        # 33. No User ID Error Message
        st.error("Please provide a User ID.")
    else:
        # 34. Initialize Progress Tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()

        results = []

        # Determine the list of files/URLs to process
        files_to_process = []

        if upload_option == "Upload Image Files" and uploaded_files:
            files_to_process = uploaded_files
        elif upload_option == "Provide Image URLs" and image_urls:
            urls = [url.strip() for url in image_urls.split("\n") if url.strip()]
            files_to_process = urls

        if not files_to_process:
            # 35. No Files to Process Warning
            st.warning("No files or URLs to process.")
        else:
            names_list = []
            if naming_option == "Custom Names List" and custom_names:
                names_list = [name.strip() for name in custom_names.split("\n")]
                if len(names_list) < len(files_to_process):
                    # 36. Insufficient Names Warning
                    st.warning(f"Warning: Only {len(names_list)} names provided for {len(files_to_process)} files. Some files will use default naming.")

            # Process each file
            for i, file_item in enumerate(files_to_process):
                # 37. Dynamic Progress Updates
                progress = (i + 1) / len(files_to_process)
                progress_bar.progress(progress)
                status_text.text(f"Processing item {i + 1} of {len(files_to_process)}")

                try:
                    if upload_option == "Upload Image Files":
                        file_name = file_item.name
                        image_bytes = file_item.getvalue()
                    else:  # URL mode
                        response = requests.get(file_item)
                        response.raise_for_status()  # Check for HTTP errors
                        image_bytes = response.content
                        file_name = file_item.split("/")[-1]

                    if naming_option == "Use Filenames":
                        name = os.path.splitext(file_name)[0]
                    elif naming_option == "Custom Naming Pattern":
                        name = name_pattern.replace("{index}", str(i + 1))
                    else:  # Custom Names List
                        name = names_list[i] if i < len(names_list) else f"Decal {i + 1}"

                    # Call the updated upload_decal function
                    result = upload_decal(api_key, image_bytes, name, description, user_id, image_type)
                    result["file"] = file_name

                    results.append(result)

                    if add_delay and i < len(files_to_process) - 1:
                        time.sleep(delay_seconds)

                except requests.exceptions.RequestException as e:
                    error_message = f"Error processing {file_item}: {e}"
                    logger.error(error_message)
                    results.append({"file": file_item, "success": False, "error": error_message})
                    continue

                except Exception as e:
                    error_message = f"Unexpected error processing {file_item}: {e}"
                    logger.error(error_message)
                    results.append({"file": file_item, "success": False, "error": error_message})
                    continue

            # 38. Display Results
            with results_container:
                st.subheader("Upload Results")

                success_count = sum(1 for r in results if r.get("success", False))
                st.markdown(f"Uploaded **{success_count}** of **{len(results)}** items successfully.")

                # 39. Results as Dataframe
                results_df = pd.DataFrame(results)
                st.dataframe(results_df)

                # 40. CSV Download Button
                csv = results_df.to_csv(index=False)
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name="roblox_upload_results.csv",
                    mime="text/csv",
                )

# 41. App Note in Footer
st.markdown("---")
st.markdown("**Note:** This tool uses the Roblox API. Ensure compliance with Roblox's Terms of Service when uploading content.")
