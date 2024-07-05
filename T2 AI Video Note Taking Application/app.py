# Importing the necessary library
import re
import requests
import streamlit as st
from twelvelabs import TwelveLabs
from datetime import datetime
import json
import uuid

# Setting up the TwelveLabs client
API_KEY = "Your API KEY"
API_URL = "https://api.twelvelabs.io/v1.2"
INDEXES_URL = f"{API_URL}/indexes"

# For the validation of the TwelveLabs
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

# CSS Design
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; font-weight: bold; color: #1E90FF; text-align: center; margin-bottom: 30px;}
    .sub-header {font-size: 1.8rem; font-weight: bold; color: #4682B4; margin-top: 30px; margin-bottom: 20px;}
    .note-box {border: 1px solid #ddd; padding: 15px; border-radius: 8px; margin-bottom: 20px; background-color: #f9f9f9;}
    .note-title {font-weight: bold; color: #4682B4; font-size: 1.2rem;}
    .note-content {font-style: italic; color: #333; margin-top: 10px;}
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        transition-duration: 0.4s;
        cursor: pointer;
        border-radius: 12px;
        border: none;
    }
    .stButton>button:hover {background-color: #45a049;}
</style>
""", unsafe_allow_html=True)

# Heading of the Application
st.markdown("<h1 class='main-header'>📝 AI Video Note Taking App</h1>", unsafe_allow_html=True)
st.markdown("Transform your favorite YouTube videos into insightful notes with AI powered analysis.")

# To initialize the session state to save the progress
if 'notes' not in st.session_state:
    st.session_state.notes = []
if 'show_popup' not in st.session_state:
    st.session_state.show_popup = False
if 'current_note' not in st.session_state:
    st.session_state.current_note = None

# Utility function to validate YouTube URL by using the regex
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
def process_video(index_id, url):
    # Create task

    try:
        task = client.task.external_provider(index_id=index_id, url=url)
        
        def on_task_update(task):
            st.write(f"Status: {task.status}")

        task.wait_for_done(sleep_interval=5, callback=on_task_update)
        
        if task.status == "ready":
            st.success("Video indexed successfully! 🎉")
            return client.task.retrieve(id=task.id).video_id
        else:
            st.error(f"Video processing failed with status - {task.status}")
            return None
        
    except Exception as e:
        st.error(f"An error occurred - {str(e)}")
        return None

def save_notes():
    with open("notes.json", "w") as f:
        json.dump(st.session_state.notes, f)

def load_notes():
    try:
        with open("notes.json", "r") as f:
            st.session_state.notes = json.load(f)
    except FileNotFoundError:
        st.session_state.notes = []

# Load existing notes
load_notes()

# Main Section of the Application
if st.button("➕ Add New Note", key="add_note"):
    st.session_state.show_popup = True
    

if st.session_state.show_popup:
    st.markdown("<h2 class='sub-header'>🆕 Create New Note</h2>", unsafe_allow_html=True)
    with st.form("new_note_form"):
        youtube_url = st.text_input("YouTube Video URL")
        prompt = st.text_area("Analysis Prompt", "Summarize the main points of this video.")
        custom_tags = st.text_input("Custom Tags (comma-separated)")
        submitted = st.form_submit_button("Create Note")

        if submitted:
            if not is_valid_youtube_url(youtube_url):
                st.error("Invalid YouTube URL. Please enter a valid YouTube video URL.")
            elif not is_url(youtube_url):
                st.error("The provided URL is not accessible. Please check the URL.")
            else:
                with st.spinner("Processing video and generating note..."):
                    try:
                        index_name = f"index_{datetime.now().strftime('%Y%m%d%H%M%S')}"

                        # Engines of TwelveLabs
                        engines_config = [
                            {"name": "pegasus1.1", "options": ["visual", "conversation"]},
                            {"name": "marengo2.6", "options": ["visual", "conversation", "text_in_video", "logo"]}
                        ]
                        index = client.index.create(name=index_name, engines=engines_config)
                        video_id = process_video(index.id, youtube_url)

                        if video_id:
                            result = client.generate.text(video_id=video_id, prompt=prompt)
                            new_note = {
                                "id": str(uuid.uuid4()),
                                "url": youtube_url,
                                "prompt": prompt,
                                "content": result.data,
                                "tags": [tag.strip() for tag in custom_tags.split(',') if tag.strip()],
                                "created_at": datetime.now().isoformat()
                            }
                            st.session_state.notes.append(new_note)
                            save_notes()
                            st.success("Note added successfully!")
                            st.session_state.show_popup = False
                            
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

# Display existing notes
st.markdown("<h2 class='sub-header'>📚 Your Notes</h2>", unsafe_allow_html=True)

# Search and filter
search_query = st.text_input("🔍 Search notes", "")
tag_filter = st.multiselect("🏷️ Filter by tags", list(set([tag for note in st.session_state.notes for tag in note['tags']])))

filtered_notes = [note for note in st.session_state.notes 
                  if search_query.lower() in note['content'].lower() 
                  and (not tag_filter or any(tag in note['tags'] for tag in tag_filter))]

for note in filtered_notes:
    st.markdown(f"<div class='note-box'>", unsafe_allow_html=True)
    st.markdown(f"<p class='note-title'>YouTube URL: {note['url']}</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='note-title'>Prompt:</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='note-content'>{note['prompt']}</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='note-title'>Content:</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='note-content'>{note['content']}</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='note-title'>Tags: {', '.join(note['tags'])}</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✏️ Edit", key=f"edit_{note['id']}"):
            st.session_state.current_note = note
    with col2:
        if st.button("🗑️ Delete", key=f"delete_{note['id']}"):
            st.session_state.notes.remove(note)
            save_notes()
            st.experimental_rerun()

# Edit note
if st.session_state.current_note:
    st.markdown("<h2 class='sub-header'>✏️ Edit Note</h2>", unsafe_allow_html=True)
    with st.form("edit_note_form"):
        edited_prompt = st.text_area("Edit Prompt", st.session_state.current_note['prompt'])
        edited_content = st.text_area("Edit Content", st.session_state.current_note['content'])
        edited_tags = st.text_input("Edit Tags", ', '.join(st.session_state.current_note['tags']))
        
        if st.form_submit_button("Save Changes"):
            for note in st.session_state.notes:
                if note['id'] == st.session_state.current_note['id']:
                    note['prompt'] = edited_prompt
                    note['content'] = edited_content
                    note['tags'] = [tag.strip() for tag in edited_tags.split(',') if tag.strip()]
                    break
            save_notes()
            st.session_state.current_note = None
            st.success("Note updated successfully!")
            st.experimental_rerun()

# Reset button
if st.button("🗑️ Clear All Notes"):
    if st.checkbox("Are you sure? This action cannot be undone."):
        st.session_state.notes = []
        save_notes()
        st.success("All notes cleared!")
        st.experimental_rerun()
