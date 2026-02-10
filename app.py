import streamlit as st
import tempfile
from pathlib import Path
from PIL import Image
from rembg import remove, new_session
import zipfile
import base64
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Background Remover",
    page_icon="🖼️",
    layout="wide"
)

# --- App Title and Description ---
st.title("🖼️ AI Background Remover")
st.markdown("""
Upload one or multiple images to instantly remove their backgrounds.
Download individual transparent PNGs or get all processed images in a ZIP file.
""")

# --- Session State Initialization ---
if 'processed_images' not in st.session_state:
    st.session_state.processed_images = {}

# --- Helper Functions ---
def process_single_image(image_file, session, use_alpha_matting=False):
    """Process a single uploaded image to remove its background."""
    try:
        input_image = Image.open(image_file)
        # Apply background removal
        output_image = remove(input_image, session=session, alpha_matting=use_alpha_matting)
        
        # Convert to bytes for download
        buf = io.BytesIO()
        output_image.save(buf, format='PNG')
        byte_im = buf.getvalue()
        
        return output_image, byte_im
    except Exception as e:
        st.error(f"Error processing {image_file.name}: {str(e)}")
        return None, None

def get_zip_download_link(zip_buffer, filename="processed_images.zip"):
    """Generate a download link for a ZIP file."""
    b64 = base64.b64encode(zip_buffer.getvalue()).decode()
    return f'<a href="data:application/zip;base64,{b64}" download="{filename}">📥 Download All Images as ZIP</a>'

# --- Main App Interface ---

# Sidebar for controls
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Model selection
    model_option = st.selectbox(
        "Select AI Model",
        ["General (u2net)", "Human Focus (u2net_human_seg)", "Lightweight (u2netp)"],
        help="Choose a model based on your image subject for best results."
    )
    
    # Model mapping
    model_map = {
        "General (u2net)": "u2net",
        "Human Focus (u2net_human_seg)": "u2net_human_seg",
        "Lightweight (u2netp)": "u2netp"
    }
    selected_model = model_map[model_option]
    
    # Advanced options
    with st.expander("Advanced Options"):
        use_alpha_matting = st.checkbox(
            "Enable Alpha Matting",
            value=False,
            help="Produces smoother edges, especially for hair or complex objects. May be slower."
        )
    
    st.divider()
    st.markdown("**How to use:**")
    st.markdown("""
    1. Upload images using the uploader below
    2. View results instantly
    3. Download individual images or all as ZIP
    """)

# Initialize the AI model session (for better performance in batch processing)
@st.cache_resource
def load_ai_session(model_name=selected_model):
    """Cache the AI model session to avoid reloading on every run[citation:8]."""
    return new_session(model_name)

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Upload Images")
    uploaded_files = st.file_uploader(
        "Choose image files",
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        help="Supports PNG, JPG, and JPEG formats. Select multiple for batch processing."
    )

# Process images if uploaded
if uploaded_files:
    # Initialize progress and session
    progress_bar = st.progress(0, text="Processing images...")
    session = load_ai_session(selected_model)
    
    # Clear previous results for new batch
    st.session_state.processed_images = {}
    
    # Process each image
    for i, uploaded_file in enumerate(uploaded_files):
        processed_img, img_bytes = process_single_image(
            uploaded_file, session, use_alpha_matting
        )
        
        if processed_img:
            # Store in session state
            st.session_state.processed_images[uploaded_file.name] = {
                'original_name': uploaded_file.name,
                'image': processed_img,
                'bytes': img_bytes
            }
        
        # Update progress bar
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    progress_bar.empty()
    st.success(f"✅ Successfully processed {len(st.session_state.processed_images)} image(s)!")

# Display results if we have processed images
if st.session_state.processed_images:
    with col2:
        st.subheader("📥 Download Results")
        
        # Create ZIP file for batch download
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_name, img_data in st.session_state.processed_images.items():
                zip_file.writestr(
                    f"no_bg_{Path(file_name).stem}.png",
                    img_data['bytes']
                )
        zip_buffer.seek(0)
        
        # Show batch download option
        st.markdown(get_zip_download_link(zip_buffer), unsafe_allow_html=True)
        st.caption("Contains all processed images as transparent PNGs.")
        
        st.divider()
        
        # Individual image download section
        st.subheader("Individual Downloads")
        for file_name, img_data in st.session_state.processed_images.items():
            st.download_button(
                label=f"Download: {Path(file_name).stem}.png",
                data=img_data['bytes'],
                file_name=f"no_bg_{Path(file_name).stem}.png",
                mime="image/png",
                key=f"dl_{file_name}"
            )

    # Display before/after comparison
    st.divider()
    st.subheader("🔄 Before & After Comparison")
    
    # Create columns for comparison - adjust based on number of images
    num_images = len(st.session_state.processed_images)
    cols = st.columns(min(num_images, 3))
    
    for idx, (file_name, img_data) in enumerate(st.session_state.processed_images.items()):
        col_idx = idx % 3
        with cols[col_idx]:
            # Display original and processed side by side
            comp_col1, comp_col2 = st.columns(2)
            with comp_col1:
                st.image(Image.open(io.BytesIO(uploaded_files[idx].getvalue())), 
                        caption="Original", use_column_width=True)
            with comp_col2:
                st.image(img_data['image'], 
                        caption="Background Removed", use_column_width=True)
            st.caption(f"**{Path(file_name).stem}**")
    
    # Clear results button
    if st.button("🔄 Process New Batch"):
        st.session_state.processed_images = {}
        st.rerun()

else:
    # Show placeholder when no images are processed
    with col2:
        st.info("👈 Upload images to see the magic happen!")
        st.image("https://via.placeholder.com/400x300/FFB6C1/FFFFFF?text=Preview+Will+Appear+Here", 
                caption="Processed images will appear here")

# --- Footer ---
st.divider()
st.markdown("""
---
**Powered by:** [rembg](https://github.com/danielgatis/rembg) & Streamlit  
**Models:** U²-Net for AI-powered background removal[citation:1][citation:8]  
*Processed images are not stored on any server.*
""")
