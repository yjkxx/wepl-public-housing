import os
import time
import requests
import json
import boto3
import mysql.connector
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, will use system environment variables
    pass

# API Keys and Configuration
API_KEY = os.getenv("HEYGEN_API_KEY", "MGMzNTA2MjlkZTU1NDM4NjhlMzlhZTY4ZTcyMGNmYTctMTc1Mzc2MjQ4OA==")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# YouTube API Configuration
YOUTUBE_CLIENT_SECRETS_FILE = "client_secret.json"
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']



GENERATE_URL = "https://api.heygen.com/v2/video/generate"
STATUS_URL = "https://api.heygen.com/v1/video_status.get"
HEADERS = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json"
}
payload = {
    "caption": True,
    "dimension": {"width": 1280, "height": 720},
    "video_inputs": [
        {
            "character": {
                "type": "avatar",
                "avatar_id": "Annie_expressive12_public",  # 원하는 아바타 ID
                "avatar_style": "normal"
            },
            "voice": {
                "type": "text",
                "voice_id": "bef4755ca1f442359c2fe6420690c8f7",  # 원하는 음성 ID
                "input_text": """이 곳에 스크립트를 넣어주세요."""
            },
            "background": {
                "type": "video",
                "video_asset_id": "c0178a77f6334f7d9dbb50b86a1e1661",  # 지정한 video_asset_id
                "play_style": "loop",
                "fit": "cover"
            }
        }
    ]
}
def generate_video():
    print(":앞쪽_화살표: 영상 생성 요청 중...")
    resp = requests.post(GENERATE_URL, headers=HEADERS, json=payload)
    if resp.status_code != 200:
        print(":x: 생성 요청 실패:", resp.status_code, resp.text)
        return None
    data = resp.json().get("data", {})
    vid = data.get("video_id")
    if vid:
        print(":흰색_확인_표시: 생성 요청 성공! video_id:", vid)
        with open("response_generate.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    else:
        print(":x: video_id를 찾을 수 없음:", data)
    return vid
def check_status(video_id):
    resp = requests.get(STATUS_URL, headers=HEADERS, params={"video_id": video_id})
    if resp.status_code != 200:
        print(":x: 상태 조회 실패:", resp.status_code, resp.text)
        return None
    return resp.json().get("data", {})
def download_by_url(url, filename):
    print(f":받은_편지함_트레이: 다운로드 시작 → {filename}")
    resp = requests.get(url, stream=True)
    if resp.status_code == 200:
        with open(filename, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        print(":흰색_확인_표시: 다운로드 완료:", filename)
        return True
    else:
        print(":x: 다운로드 실패:", resp.status_code)
        return False

def get_database_connection():
    """데이터베이스 연결을 반환합니다."""
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return connection
    except mysql.connector.Error as err:
        print(f":x: 데이터베이스 연결 실패: {err}")
        return None

def fetch_latest_posting_without_video():
    """비디오 URL이 없는 최신 포스팅 1개를 가져옵니다."""
    connection = get_database_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        # 테이블 구조에 맞게 쿼리를 수정해주세요
        query = """
        SELECT id, title, content, created_at 
        FROM postings 
        WHERE video_url IS NULL OR video_url = '' 
        ORDER BY created_at DESC 
        LIMIT 1
        """
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            print(f":흰색_확인_표시: 포스팅 조회 성공: {result['title']}")
            return result
        else:
            print(":x: 비디오가 없는 포스팅을 찾을 수 없습니다.")
            return None
            
    except mysql.connector.Error as err:
        print(f":x: 포스팅 조회 실패: {err}")
        return None

def generate_script_from_template(posting_data):
    """포스팅 데이터로부터 간단한 템플릿 기반 비디오 스크립트를 생성합니다."""
    try:
        # 간단한 템플릿 기반 스크립트 생성 (AI 모델 사용 안함)
        title = posting_data['title']
        content = posting_data['content']
        
        # 템플릿 기반 스크립트 생성
        script = f"""안녕하세요! 오늘은 {title}에 대해 알려드리겠습니다.

{content}

이상으로 {title}에 대한 내용을 전해드렸습니다. 더 자세한 정보가 필요하시면 언제든지 문의해 주세요. 감사합니다!"""
        
        print(f":흰색_확인_표시: 템플릿 기반 스크립트 생성 완료")
        print(f"생성된 스크립트: {script[:100]}...")
        
        return script
        
    except Exception as e:
        print(f":x: 스크립트 생성 실패: {e}")
        return None

def upload_to_s3(file_path, s3_key):
    """파일을 S3에 업로드하고 URL을 반환합니다."""
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        
        s3_client.upload_file(file_path, S3_BUCKET_NAME, s3_key)
        
        # S3 URL 생성
        s3_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        
        print(f":흰색_확인_표시: S3 업로드 완료: {s3_url}")
        return s3_url
        
    except Exception as e:
        print(f":x: S3 업로드 실패: {e}")
        return None

def get_youtube_service():
    """YouTube API 서비스 객체를 반환합니다."""
    creds = None
    
    # 토큰 파일이 있으면 로드
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', YOUTUBE_SCOPES)
    
    # 유효한 자격 증명이 없으면 인증 플로우 실행
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                YOUTUBE_CLIENT_SECRETS_FILE, YOUTUBE_SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 토큰 저장
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('youtube', 'v3', credentials=creds)

def upload_to_youtube(video_file_path, title, description):
    """비디오를 YouTube에 업로드하고 비디오 ID를 반환합니다."""
    try:
        youtube = get_youtube_service()
        
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': ['AI', '자동생성', '공공주택'],
                'categoryId': '22'  # People & Blogs
            },
            'status': {
                'privacyStatus': 'public',  # 'private', 'unlisted', 'public'
                'selfDeclaredMadeForKids': False
            }
        }
        
        media = MediaFileUpload(
            video_file_path,
            chunksize=-1,
            resumable=True,
            mimetype='video/mp4'
        )
        
        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if response is not None:
                    if 'id' in response:
                        video_id = response['id']
                        print(f":흰색_확인_표시: YouTube 업로드 완료: {video_id}")
                        return video_id
                    else:
                        print(f":x: YouTube 업로드 실패: {response}")
                        return None
            except Exception as e:
                error = str(e)
                retry += 1
                if retry > 3:
                    print(f":x: YouTube 업로드 최대 재시도 초과: {error}")
                    return None
                print(f":warning: YouTube 업로드 재시도 {retry}: {error}")
                time.sleep(2 ** retry)
        
    except Exception as e:
        print(f":x: YouTube 업로드 실패: {e}")
        return None

def get_youtube_embed_url(video_id):
    """YouTube 비디오 ID로부터 임베드 URL을 생성합니다."""
    embed_url = f"https://www.youtube.com/embed/{video_id}"
    print(f":흰색_확인_표시: YouTube 임베드 URL 생성: {embed_url}")
    return embed_url

def update_posting_with_video_urls(posting_id, s3_url, youtube_embed_url):
    """포스팅에 비디오 URL들을 업데이트합니다."""
    connection = get_database_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        # 테이블 구조에 맞게 쿼리를 수정해주세요
        query = """
        UPDATE postings 
        SET video_url = %s, youtube_embed_url = %s, updated_at = %s
        WHERE id = %s
        """
        cursor.execute(query, (s3_url, youtube_embed_url, datetime.now(), posting_id))
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f":흰색_확인_표시: 포스팅 업데이트 완료: ID {posting_id}")
        return True
        
    except mysql.connector.Error as err:
        print(f":x: 포스팅 업데이트 실패: {err}")
        return False

def generate_video_with_script(script_text):
    """스크립트를 사용하여 비디오를 생성합니다."""
    # 기존 payload를 복사하고 스크립트 업데이트
    video_payload = payload.copy()
    video_payload["video_inputs"][0]["voice"]["input_text"] = script_text
    
    print(":앞쪽_화살표: 영상 생성 요청 중...")
    resp = requests.post(GENERATE_URL, headers=HEADERS, json=video_payload)
    if resp.status_code != 200:
        print(":x: 생성 요청 실패:", resp.status_code, resp.text)
        return None
    
    data = resp.json().get("data", {})
    vid = data.get("video_id")
    if vid:
        print(":흰색_확인_표시: 생성 요청 성공! video_id:", vid)
        with open("response_generate.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    else:
        print(":x: video_id를 찾을 수 없음:", data)
    return vid

def process_complete_workflow():
    """전체 워크플로우를 처리합니다."""
    print("🚀 전체 워크플로우 시작")
    
    # 1. 최신 포스팅 조회
    posting_data = fetch_latest_posting_without_video()
    if not posting_data:
        print("❌ 처리할 포스팅이 없습니다.")
        return
    
    # 2. 템플릿 기반 스크립트 생성
    script = generate_script_from_template(posting_data)
    if not script:
        print("❌ 스크립트 생성에 실패했습니다.")
        return
    
    # 3. HeyGen으로 비디오 생성
    video_id = generate_video_with_script(script)
    if not video_id:
        print("❌ 비디오 생성에 실패했습니다.")
        return
    
    # 4. 비디오 생성 완료까지 대기
    video_url = None
    for attempt in range(15):
        time.sleep(20)
        data = check_status(video_id)
        if not data:
            print("❌ 비디오 상태 확인에 실패했습니다.")
            return
        
        status = data.get("status")
        print(f"{attempt+1}/15 ⏳ 현재 상태: {status}")
        
        if status == "completed":
            caption_url = data.get("video_url_caption") or data.get("caption_video_url") or data.get("captioned_video_url")
            if caption_url:
                video_filename = f"video_{posting_data['id']}_{int(time.time())}.mp4"
                if download_by_url(caption_url, video_filename):
                    video_url = caption_url
                    break
            else:
                print("❌ 자막 포함 URL을 찾을 수 없습니다.")
                return
        elif status == "failed":
            print(f"❌ 생성 실패: {data.get('error')}")
            return
    
    if not video_url:
        print("❌ 최대 재시도 초과 — 영상 생성 완료되지 않았습니다.")
        return
    
    # 5. S3에 업로드
    s3_key = f"videos/{posting_data['id']}/{video_filename}"
    s3_url = upload_to_s3(video_filename, s3_key)
    if not s3_url:
        print("❌ S3 업로드에 실패했습니다.")
        return
    
    # 6. YouTube에 업로드
    youtube_video_id = upload_to_youtube(
        video_filename,
        f"[AI 생성] {posting_data['title']}",
        f"AI가 자동으로 생성한 공공주택 정보 영상입니다.\n\n{posting_data['content'][:500]}..."
    )
    if not youtube_video_id:
        print("❌ YouTube 업로드에 실패했습니다.")
        return
    
    # 7. YouTube 임베드 URL 생성
    youtube_embed_url = get_youtube_embed_url(youtube_video_id)
    
    # 8. 데이터베이스 업데이트
    if update_posting_with_video_urls(posting_data['id'], s3_url, youtube_embed_url):
        print("🎉 전체 워크플로우 완료!")
        print(f"📊 포스팅 ID: {posting_data['id']}")
        print(f"☁️ S3 URL: {s3_url}")
        print(f"📺 YouTube 임베드: {youtube_embed_url}")
    else:
        print("❌ 데이터베이스 업데이트에 실패했습니다.")
    
    # 임시 파일 정리
    if os.path.exists(video_filename):
        os.remove(video_filename)
        print(f"🗑️ 임시 파일 삭제: {video_filename}")
def main():
    """기존 단일 비디오 생성 또는 전체 워크플로우 실행"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--workflow":
        # 전체 워크플로우 실행
        process_complete_workflow()
    else:
        # 기존 방식: 단일 비디오 생성
        vid = generate_video()
        if not vid:
            return
        for attempt in range(15):
            time.sleep(20)
            data = check_status(vid)
            if not data:
                return
            status = data.get("status")
            print(f"{attempt+1}/15 :앞쪽_화살표: 현재 상태: {status}")
            if status == "completed":
                caption_url = data.get("video_url_caption") or data.get("caption_video_url") or data.get("captioned_video_url")
                if caption_url:
                    download_by_url(caption_url, "captioned_video.mp4")
                else:
                    print(":x: 자막 포함 URL을 찾을 수 없습니다.")
                return
            elif status == "failed":
                print(":x: 생성 실패:", data.get("error"))
                return
        print(":x: 최대 재시도 초과 — 영상 생성 완료되지 않았습니다.")
if __name__ == "__main__":
    main()