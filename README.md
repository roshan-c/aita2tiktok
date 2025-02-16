# Reddit AITA to TikTok TTS Generator

This project automates the process of converting Reddit AITA (Am I The Asshole?) stories into TTS (Text-to-Speech) audio files for creating TikTok storytime videos. It fetches top stories from r/AmItheAsshole, generates high-quality TTS using Microsoft Edge's voice synthesis, and creates corresponding subtitle files.

## Features

- Fetches top stories from r/AmItheAsshole subreddit
- Converts text to speech using Microsoft Edge's natural-sounding voices
- Generates synchronized subtitles for video creation
- Processes multiple stories concurrently
- Cleans and formats Reddit markdown text
- Creates organized output with audio and subtitle files

## Prerequisites

- Python 3.7 or higher
- A Reddit API account (for PRAW)

## Setup

1. Clone this repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root with your Reddit API credentials:
   ```
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   ```

## Usage

1. Run the script:
   ```
   python aita_to_speech.py
   ```

2. The script will:
   - Fetch the top 10 AITA stories of the day
   - Generate MP3 audio files using TTS
   - Create corresponding subtitle files
   - Save everything in the `output` directory

3. Output files are named using the format:
   - Audio: `story_title_YYYYMMDD_HHMMSS.mp3`
   - Subtitles: `story_title_YYYYMMDD_HHMMSS.txt`

The generated files can be used with video editing software to create TikTok storytime content.

## Note

Please ensure you comply with Reddit's content usage policies and TikTok's guidelines when creating and publishing content.