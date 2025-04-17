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

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
CLEAN_WORDS = ["sky", "blue", "cloud", "star", "moon", "sun", "rainbow", "tree",
               "flower", "river", "mountain", "ocean", "forest", "meadow", "bird",
               "dolphin", "panda", "robot", "rocket", "planet", "galaxy", "comet"]
ROBLOX_ASSETS_API = "https://apis.roblox.com/assets/v1/assets"
ROBLOX_CLOUD_AUTH_API = "https://apis.roblox.com/cloud-authentication/v1/apiKey"

# 1. Custom Theme
st.set_page_config(page_title="Roblox Decal Uploader", page_icon="🎮", layout="wide")

# 2. Improved Styling with Markdown/CSS
st.markdown("""
    <style>
        .reportview-container { background: #f0f2f6; }
        .css-12oz5g7 { padding: 1rem 1rem; }
        .stButton>button { color: #4F8BF9; border-color: #4F8BF9; }
        .stButton>button:hover { color: white; background-color : #4F8BF9; }
        .stTextInput>label { color: #4F8BF9; }
        .stTextArea>label { color: #4F8BF9; }
        .stProgress>div>div { background-color: #4F8BF9 !important; }
        .stSuccess { color: green; }
        .stError { color: red; }
    </style>
""", unsafe_allow_html=True)

# 3. App Title with Emojis
st.title("Roblox Decal Mass Uploader 🎮🖼️")
st.markdown("Effortlessly upload multiple decals to Roblox using the Roblox API. Ensure compliance with Roblox's Terms of Service.")

# 4. Enhanced Sidebar
with st.sidebar:
    st.header("API & Authentication")

    # 5. API Key Method Selection
    api_key_method = st.radio("API Key Source", ["Enter Existing Key", "Generate from Cookie"])

    api_key = None

    if api_key_method == "Enter Existing Key":
        # 6. API Key Input Field
        api_key = st.text_input("Enter your Roblox API Key", type="password")
        # 7. API Key Validation Check
        if api_key:
            st.success("API Key entered successfully!")
    else:
        # 8. Cookie Input Field with Security Note
        st.markdown("**Enter your .ROBLOSECURITY cookie (sensitive data)**")
        cookie = st.text_area("Cookie value will be hidden when typing", height=100)
        # 9. API Key Generation Button
        if st.button("Generate API Key from Cookie"):
            # 10. Animated Spinner While Generating API Key
            with st.spinner("Generating API Key..."):
                api_key = create_api_key(cookie)
                if api_key:
                    # 11. Success Message with Expandable Code
                    st.success("API Key generated successfully!")
                    st.markdown("**Your API Key (click to reveal):**")
                    expander = st.expander("Show API Key")
                    with expander:
                        st.code(api_key)
                else:
                    # 12. Error Message
                    st.error("Failed to generate API Key. Check logs for details.")

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


def upload_decal(api_key: str, image_bytes: bytes, name: str, description: str = "", image_type: str = "image/png") -> Dict:
    headers = {
        "x-api-key": api_key
    }

    files = {
        'request': (None, json.dumps({
            "assetType": "Decal",
            "displayName": name,
            "description": description
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

# 15. Upload Method Selection
upload_option = st.radio("Image Source", ["Upload Image Files", "Provide Image URLs"])

# Add an image type selection
image_type = st.selectbox("Image Type", ["image/png", "image/jpeg"])

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
                img = Image.open(file)
                st.image(img, caption=file.name, width=150)

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
                    st.image(img, caption=f"URL {i + 1}", width=150)
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
                    result = upload_decal(api_key, image_bytes, name, description, image_type)
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
