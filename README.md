# AITA to TikTok Video Generator

An automated tool that converts Reddit's r/AmItheAsshole posts into TikTok-style videos with text-to-speech narration and dynamic subtitles, and automatically uploads them to TikTok.

## Features

- Fetches top stories from r/AmItheAsshole subreddit
- Generates text-to-speech narration using Microsoft Edge TTS
- Creates dynamic subtitles synchronized with speech
- Generates thumbnail images with post titles and statistics
- Produces vertical format videos (1080x1920) suitable for TikTok
- Includes background video templates
- Shows upvotes and comment counts in thumbnails
- Automatically uploads videos to TikTok with generated captions and relevant hashtags
- Handles video upload scheduling and rate limiting

## Requirements

- Python 3.11+
- Required Python packages (install via `pip install -r requirements.txt`):
  - praw (Reddit API wrapper)
  - markdown
  - edge-tts
  - python-dotenv
  - Pillow
  - moviepy
  - tiktok-uploader (for TikTok integration)

## Setup

1. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your Reddit API and TikTok credentials:
   ```
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   TIKTOK_SESSION_ID=your_tiktok_session_id
   ```

   To get your TikTok session ID:
   1. Log into TikTok in your web browser
   2. Open DevTools (F12)
   3. Go to Application > Cookies
   4. Find and copy the value of the 'sessionid' cookie

3. Ensure you have the following files in your project directory:
   - `template.png` - Template image for thumbnails
   - `template.mp4` - Background video template
   - `arial.ttf` - Arial font file for text rendering

## Usage

Run the script to process the top AITA posts of the day:

```bash
python aita_to_speech.py
```

The script will:
1. Fetch the top posts from r/AmItheAsshole
2. Generate TTS audio for each post
3. Create thumbnail images
4. Generate videos with subtitles and background
5. Save all outputs in timestamped folders under the `output/` directory

## Output Structure

Generated files are organized in timestamped folders:
```
output/
└── YYYYMMDD_HHMMSS/
    ├── post_title_timestamp.mp3 (audio)
    ├── post_title_timestamp.json (subtitle data)
    ├── post_title_timestamp.png (thumbnail)
    └── post_title_timestamp.mp4 (final video)
```

## Configuration

The script includes configurable parameters for:
- Video dimensions (1080x1920)
- Font sizes and colors
- Text positioning
- Frame rate
- Output paths

These can be modified in the `aita_to_speech.py` file.

## Requirements

See `requirements.txt` for a complete list of Python package dependencies.