# AI Video Generator Setup Guide

This script automates the process of:
1. Fetching the latest posting without a video URL from your database
2. Generating a script using a simple template (lightweight, no AI model calls)
3. Creating an AI video using HeyGen
4. Uploading the video to AWS S3
5. Publishing the video to YouTube
6. Updating the database with video URLs

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
1. Copy `.env.example` to `.env`
2. Fill in all the required API keys and configuration values

### 3. Database Setup
Make sure your database has a table with the following structure (adjust table name and column names in the code as needed):

```sql
CREATE TABLE postings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    video_url VARCHAR(500) NULL,
    youtube_embed_url VARCHAR(500) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 4. YouTube API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3
4. Create credentials (OAuth2 client ID) for a desktop application
5. Download the JSON file and save it as `client_secret.json` in the project directory

### 5. AWS S3 Setup
1. Create an S3 bucket
2. Set up IAM user with S3 upload permissions
3. Configure the bucket for public read access if needed

### 6. API Keys Required
- **HeyGen API Key**: Get from HeyGen dashboard
- **AWS Credentials**: Get from AWS IAM console

Note: Gemini API is no longer required as script generation now uses lightweight templates.

## Usage

### Run Complete Workflow
```bash
python ai_api.py --workflow
```

### Run Single Video Generation (Original functionality)
```bash
python ai_api.py
```

## Workflow Process

1. **Database Query**: Fetches the latest posting where `video_url` is NULL or empty
2. **Script Generation**: Uses a simple template to create a natural video script from the posting content (no AI model calls)
3. **Video Creation**: Sends the script to HeyGen API to generate an AI video
4. **Status Monitoring**: Polls HeyGen API until video generation is complete
5. **S3 Upload**: Uploads the generated video to your S3 bucket
6. **YouTube Upload**: Publishes the video to your YouTube channel
7. **Database Update**: Updates the posting record with both S3 and YouTube URLs
8. **Cleanup**: Removes temporary local video files

## Customization

### Video Settings
Modify the `payload` dictionary in the script to change:
- Avatar ID and style
- Voice ID
- Background video
- Video dimensions

### Script Generation
Modify the template in `generate_script_from_template()` to change how scripts are generated.

### Database Schema
Update the SQL queries in the following functions if your table structure is different:
- `fetch_latest_posting_without_video()`
- `update_posting_with_video_urls()`

## Error Handling

The script includes comprehensive error handling and will print detailed status messages. Check the console output for any issues with:
- Database connections
- API responses
- File uploads
- Authentication

## Notes

- First run will require YouTube OAuth authentication in your browser
- Video generation can take several minutes
- Make sure your S3 bucket has proper CORS settings if serving videos on web
- YouTube uploads are set to public by default (change in `upload_to_youtube()` function)
