from flask import Flask, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import google.generativeai as genai
import os

app = Flask(__name__)

# Configure Google Gemini API
GOOGLE_API_KEY = 'AIzaSyBJk0fGQlA54CgIP7tH9DYNzn1xzOUofe4'  # You should move this to an environment variable
genai.configure(api_key=GOOGLE_API_KEY)

def extract_video_id(video_url):
    """
    Extracts the video ID from a YouTube video URL.

    Args:
        video_url (str): The YouTube video URL.

    Returns:
        str or None: The video ID, or None if it cannot be extracted.
    """
    try:
        parsed_url = urlparse(video_url)
        if 'youtube.com' in parsed_url.netloc:
            if parsed_url.path == '/watch':
                query_params = parse_qs(parsed_url.query)
                if 'v' in query_params:
                    return query_params['v'][0]
            elif parsed_url.path.startswith('/embed/'):
                return parsed_url.path.split('/')[2]
            elif parsed_url.path.startswith('/shorts/'):
                return parsed_url.path.split('/')[2]
            else:
                video_id = parsed_url.path.lstrip('/')
                if video_id:
                    return video_id
        elif 'youtu.be' in parsed_url.netloc:
            return parsed_url.path.lstrip('/')
        elif 'googleusercontent.com' in parsed_url.netloc:
            return parsed_url.path.split('/')[-1]

    except Exception as e:
        print(f"Error extracting video ID: {e}")
        return None
    return None

def get_transcript(video_id):
    """Get the transcript for a YouTube video."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['de', 'en', 'bn', 'hi'])
        return transcript, None
    except Exception as e:
        return None, str(e)

def analyze_transcript(transcript_text):
    """Analyze the transcript using Google's Gemini AI model."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(
            f"""Thoroughly analyze the attached file and provide a comprehensive overview of the aspects and topics covered: {transcript_text}."""
        )
        return response.text, None
    except Exception as e:
        return None, str(e)

@app.route('/')
def index():
    """Render the main page."""
    return render_template('main_page.html')

@app.route('/get_transcript', methods=['POST'])
def process_transcript():
    """Process the YouTube URL and return the transcript."""
    data = request.json
    youtube_url = data.get('youtube_url', '')
    analyze = data.get('analyze', False)
    
    # Extract video ID from URL
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL. Please provide a valid URL.'}), 400
    
    # Get transcript
    transcript, error = get_transcript(video_id)
    if error:
        return jsonify({'error': f'Error getting transcript: {error}'}), 400
    
    # Format transcript
    formatted_transcript = ""
    for item in transcript:
        formatted_transcript += f"{item['text']} "
    
    result = {
        'video_id': video_id,
        'transcript': formatted_transcript,
        'transcript_segments': transcript
    }
    
    # Analyze transcript if requested
    if analyze:
        analysis, analysis_error = analyze_transcript(formatted_transcript)
        if analysis_error:
            result['analysis_error'] = analysis_error
        else:
            result['analysis'] = analysis
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)