import re
import requests
import streamlit as st
from twelvelabs import TwelveLabs
from datetime import datetime

# Setting up the TwelveLabs client
API_KEY = "<Your_TwelveLabs_API_KEY>"
API_URL = "https://api.twelvelabs.io/v1.2"
INDEXES_URL = f"{API_URL}/indexes"
client = TwelveLabs(api_key=API_KEY)

# Customization of the Background of the Application
page_element = """
<style>
[data-testid="stAppViewContainer"]{
background-image: url("https://wallpapercave.com/wp/wp3589963.jpg");
background-size: cover;
}
[data-testid="stHeader"]{
background-color: rgba(0,0,0,0);
}
</style>
"""

st.markdown(page_element, unsafe_allow_html=True)

# Heading of the Application
st.markdown("<h1 style='text-align: center';>Talking with the Video 💬</h1>", unsafe_allow_html=True)
st.markdown("---")


#  To initialize the session state to save the progress
if 'video_id' not in st.session_state:
    st.session_state.video_id = None
if 'video_processed' not in st.session_state:
    st.session_state.video_processed = False
if 'index_id' not in st.session_state:
    st.session_state.index_id = None

# Utility function to validate YouTube URL
def is_valid_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    return bool(re.match(youtube_regex, url))

def is_url(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

# Function to process the video
def process_video(index_id, file=None, url=None):
    try:
        # Create task
        if file:
            task = client.task.create(index_id=index_id, file=file)
        elif url:
            task = client.task.create(index_id=index_id, url=url)
        
        st.info("Processing video... This may take a few minutes to process")

        def on_task_update(task):
            st.write(f"Status - {task.status}")

        task.wait_for_done(sleep_interval=5, callback=on_task_update)
        
        if task.status == "ready":
            st.success("Video indexed successfully🎉!!!")
            st.session_state.video_id = task.video_id
            st.session_state.video_processed = True
        else:
            st.error(f"Video processing failed with status - {task.status}")
    except Exception as e:
        st.error(f"An error occurred - {str(e)}")


st.write("More than a transcription, you can generate anything by understanding and see the unseen!!!")

# Add radio button for choosing between the option upload and YouTube URL
video_source = st.radio("Choose video source:", ("Upload Video", "YouTube URL"))

if video_source == "Upload Video":
    uploaded_file = st.file_uploader("Upload a video file", type=["mp4", "mov", "avi"])
    if uploaded_file is not None:
        st.video(uploaded_file)
        if st.button("Prepare the Indexing of the Video"):
            try:
                # Create a new index
                index_name = f"index_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                engines_config = [
                    {
                        "name": "pegasus1",
                        "options": ["visual", "conversation"]
                    },
                    {
                        "name": "marengo2.6",
                        "options": ["visual", "conversation", "text_in_video", "logo"]
                    }
                ]
                index = client.index.create(
                    name=index_name,
                    engines=engines_config
                )
                st.success(f"Index created - {index_name}")
                st.session_state.index_id = index.id

                process_video(st.session_state.index_id, file=uploaded_file)
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

else:
    youtube_url = st.text_input("Enter the YouTube Video URL")
    if youtube_url:
        if st.button("Prepare the Indexing of the Video"):
            if not is_valid_youtube_url(youtube_url):
                st.error("Invalid YouTube URL. Please enter a valid YouTube video URL.")
            elif not is_url(youtube_url):
                st.error("The provided URL is not accessible or valid. Please check the URL.")
            else:
                st.success("Valid YouTube URL. Proceeding with the indexing of video")
                try:
                    # Create a new index
                    index_name = f"index_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    engines_config = [
                        {
                            "name": "pegasus1",
                            "options": ["visual", "conversation"]
                        },
                        {
                            "name": "marengo2.6",
                            "options": ["visual", "conversation", "text_in_video", "logo"]
                        }
                    ]
                    index = client.index.create(
                        name=index_name,
                        engines=engines_config
                    )
                    st.success(f"Index created - {index_name}")
                    st.session_state.index_id = index.id

                    process_video(st.session_state.index_id, url=youtube_url)
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

# Prompt input and submit button, if video has been processed
if st.session_state.video_processed:
    user_prompt = st.text_area("Enter your prompt -", "Prepare the scene by scene script from the context video provided.")
    
    if st.button("Generate Text"):
        try:
            result = client.generate.text(
                video_id=st.session_state.video_id,
                prompt=user_prompt
            )
            st.subheader("Generated Text - ")
            st.write(result.data)
        except Exception as e:
            st.error(f"An error occurred while generating text - {str(e)}")