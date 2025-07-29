import requests
import asyncio
import aiohttp
import ssl
import json
import os
import pymysql
from decimal import Decimal
import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


def get_secret():
    """
    Retrieve secrets from AWS Secrets Manager.
    Works in both Lambda and local environments.
    """
    secret_name = os.environ.get('SECRET_NAME', "wepl-lambda-secrets")
    region_name = os.environ.get('AWS_REGION', "ap-northeast-2")

    try:
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )

        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
        
    except (ClientError, NoCredentialsError) as e:
        # In Lambda, this should not happen if IAM is set up correctly
        # In local development, this is expected if AWS credentials are not configured
        print(f"AWS Secrets Manager access failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error accessing secrets: {e}")
        return None


def is_lambda_environment():
    """Check if running in AWS Lambda environment"""
    return os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None


# Initialize secrets with environment-aware fallback
def initialize_secrets():
    """Initialize secrets with proper fallback for local vs Lambda environments"""
    
    # Try to get secrets from AWS Secrets Manager
    secrets = get_secret()
    
    if secrets:
        print("✅ Successfully loaded secrets from AWS Secrets Manager")
        return {
            'api_url_hug': secrets.get('api_url_hug'),
            'api_url_lh': secrets.get('api_url_lh'),
            'DB_HOST': secrets.get('DB_HOST'),
            'DB_PORT': secrets.get('DB_PORT', 3306),
            'DB_NAME': secrets.get('DB_NAME'),
            'DB_USER': secrets.get('DB_USER'),
            'DB_PASSWORD': secrets.get('DB_PASSWORD'),
            'GEMINI_API_KEY_PLAINTEXT': secrets.get('GEMINI_API_KEY_PLAINTEXT'),
            'KAKAO_API': secrets.get('KAKAO_API'),
            'YOUTUBE_API_KEY': secrets.get('YOUTUBE_API_KEY')
        }
    else:
        # Fallback values - different behavior for Lambda vs local
        if is_lambda_environment():
            # In Lambda, we should have secrets - this is an error
            raise Exception("❌ CRITICAL: Running in Lambda but could not access AWS Secrets Manager. Check IAM permissions.")
        else:
            # Local development - use environment variables as fallback
            print("⚠️  Running locally - using environment variables")
            return {
                'api_url_hug': os.environ.get('HUG_API_URL', ''),
                'api_url_lh': os.environ.get('LH_API_URL', ''),
                'DB_HOST': os.environ.get('DB_HOST', ''),
                'DB_PORT': int(os.environ.get('DB_PORT', '3306')),
                'DB_NAME': os.environ.get('DB_NAME', ''),
                'DB_USER': os.environ.get('DB_USER', ''),
                'DB_PASSWORD': os.environ.get('DB_PASSWORD', ''),
                'GEMINI_API_KEY_PLAINTEXT': os.environ.get('GEMINI_API_KEY', ''),
                'KAKAO_API': os.environ.get('KAKAO_API_KEY', ''),
                'YOUTUBE_API_KEY': os.environ.get('YOUTUBE_API_KEY', '')
            }


# Initialize all configuration variables
try:
    config = initialize_secrets()
    api_url_hug = config['api_url_hug']
    api_url_lh = config['api_url_lh']
    DB_HOST = config['DB_HOST']
    DB_PORT = config['DB_PORT']
    DB_NAME = config['DB_NAME']
    DB_USER = config['DB_USER']
    DB_PASSWORD = config['DB_PASSWORD']
    GEMINI_API_KEY_PLAINTEXT = config['GEMINI_API_KEY_PLAINTEXT']
    KAKAO_API = config['KAKAO_API']
    YOUTUBE_API_KEY = config['YOUTUBE_API_KEY']
    
    print(f"🚀 Configuration initialized - Environment: {'Lambda' if is_lambda_environment() else 'Local'}")
    
except Exception as e:
    print(f"❌ FATAL: Could not initialize configuration: {e}")
    raise

# --- Posting Object Format ---
# All functions use the following posting object format (all values are JSON serializable):
# {
#   'posting_id': int,
#   'posting_type_id': int or None,
#   'agency_id': str or None,
#   'area_province': str or None,
#   'area_city': str or None,
#   'address': str or None,
#   'application_start': str (YYYY-MM-DD) or None,
#   'application_end': str (YYYY-MM-DD) or None,
#   'building_type': str or None,
#   'application_url': str or None,
#   'deposit': float or None,
#   'rent': float or None,
#   'summary': str or None,
#   'rawjson': str or None,
#   's3_object_address': str or None,
#   'youtube_url': str or None
# }

def make_json_serializable(obj):
    """
    Recursively convert a posting object to a JSON-serializable dict.
    - datetime.date/datetime.datetime -> str (isoformat)
    - Decimal -> float
    """
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    elif isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj

# Fetches postings from the HUG API and returns them as a list of dictionaries.

def get_hug_api():
    try:
        response = requests.get(api_url_hug, timeout=30)
        response.raise_for_status()
        data = response.json()
        # TODO: Adjust this extraction logic to match the HUG API's actual structure
        postings = data.get('response', {}).get('body', {}).get('item', [])
        if not isinstance(postings, list):
            postings = [postings]
        return postings
    except Exception as e:
        print(f"Error fetching HUG API: {e}")
        return []

# Asynchronously fetches postings from the LH API and returns them as a list of dictionaries.
async def get_lh_api():
    try:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(api_url_lh) as response:
                response.raise_for_status()
                data = await response.json()
                items = data.get('response', {}).get('body', {}).get('item', [])
                if not isinstance(items, list):
                    items = [items]
                return items
    except Exception as e:
        print(f"Error fetching LH API: {e}")
        return []


''' db schema
mysql> describe postings;
+-------------------+---------------+------+-----+---------+-------+
| Field             | Type          | Null | Key | Default | Extra |
+-------------------+---------------+------+-----+---------+-------+
| posting_id        | int           | NO   | PRI | NULL    |       |
| posting_type_id   | int           | YES  | MUL | NULL    |       |
| agency_id         | varchar(50)   | YES  |     | NULL    |       |
| area_province     | varchar(50)   | YES  |     | NULL    |       |
| area_city         | varchar(50)   | YES  |     | NULL    |       |
| address           | varchar(500)  | YES  |     | NULL    |       |
| application_start | date          | YES  |     | NULL    |       |
| application_end   | date          | YES  |     | NULL    |       |
| building_type     | char(50)      | YES  |     | NULL    |       |
| application_url   | varchar(500)  | YES  |     | NULL    |       |
| deposit           | decimal(14,2) | YES  |     | NULL    |       |
| rent              | decimal(14,2) | YES  |     | NULL    |       |
| summary           | varchar(200)  | YES  |     | NULL    |       |
| rawjson           | json          | YES  |     | NULL    |       |
| s3_object_address | varchar(1024) | YES  |     | NULL    |       |
| youtube_url       | varchar(255)  | YES  |     | NULL    |       |
+-------------------+---------------+------+-----+---------+-------+
16 rows in set (0.01 sec)
'''

# Extracts relevant fields from the LH API JSON response and saves them to a new JSON file.
def extract_lh_fields(data):
    # Adjusted for the provided JSON structure
    items = data.get('response', {}).get('body', {}).get('item', [])
    if not isinstance(items, list):
        items = [items]
    results = []
    for item in items:
        entry = {
            'posting_id': item.get('pblancId'),
            'posting_status': item.get('sttusNm'),
            'prefecture': item.get('brtcNm'),
            'city': item.get('signguNm'),
            'detailed_address': item.get('fullAdres'),
            'posting_summary': '',  # Not in JSON, placeholder
            'application_start_date': item.get('beginDe'),
            'application_end_date': item.get('endDe'),
            'building_type': item.get('houseTyNm'),
            'housing_program_type': item.get('suplyTyNm'),
            'application_url': item.get('pcUrl'),
            'deposit': item.get('rentGtn'),
            'rent': item.get('mtRntchrg'),
        }
        results.append(entry)
    # Save extracted fields to a new JSON file
    # Print the first posting and all its details
    if results:
        print("\nFirst posting details:")
        for k, v in results[0].items():
            print(f"{k}: {v}")
    else:
        print("No postings found in LH API data.")
    
    return results


#todo: def fill_missing_fields_hug(hugpostingobj)
# skipping this part, using dummy instead


# Inserts postings from a JSON file into the MySQL database (updated for new schema).
def insert_postings_to_db(json_path):
    with open(json_path, encoding='utf-8') as f:
        postings = json.load(f)

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        db=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4'
    )

    try:
        with conn.cursor() as cur:
            sql = (
                "INSERT INTO postings "
                "(status, region_province, region_city, address_detail, apply_start, apply_end, "
                "house_type, supply_type_id, application_url, deposit, monthly_rent, agency_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            )
            values = []
            for p in postings:
                val_tuple = (
                    'Y' if p['posting_status'] == '일반공고' else 'N',
                    p['prefecture'],
                    p['city'],
                    (p['detailed_address'] or '')[:20],
                    p['application_start_date'],
                    p['application_end_date'],
                    p['building_type'],
                    int(p['housing_program_type']) if p['housing_program_type'] and str(p['housing_program_type']).isdigit() else None,
                    p['application_url'],
                    float(p['deposit']) if p['deposit'] is not None else None,
                    float(p['rent']) if p['rent'] is not None else None,
                    1  # agency_id, set to 1 for LH, change as needed
                )
                values.append(val_tuple)
            print("\nDB Write Query:")
            print(sql)
            print("Values:")
            for v in values:
                print(v)
            cur.executemany(sql, values)
        conn.commit()
        print("All postings inserted into DB.")
    finally:
        conn.close()


# Retrieves existing posting IDs from the database to avoid duplicates.
def get_existing_posting_ids():
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        db=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4'
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT posting_id FROM postings")
            rows = cur.fetchall()
            return set(str(row[0]) for row in rows)
    finally:
        conn.close()


# Filters out postings that already exist in the database based on posting_id.
def filter_new_postings(postings):
    existing_ids = get_existing_posting_ids()
    # Use 'posting_id' as the unique key in your posting object
    new_postings = [p for p in postings if str(p.get('posting_id')) not in existing_ids]
    return new_postings


# send new posting object to gemini api and get one sentence summary, return object with summary
def get_ai_summary_for_posting(posting):
    
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    GEMINI_API_KEY = GEMINI_API_KEY_PLAINTEXT
    # Compose prompt
    prompt = f"""
    다음은 한국 공공임대주택 공고 데이터입니다. 이 정보를 바탕으로 이 공고의 특별하거나 차별된 점을 60글자 이내 한문장, 입니다체로 요약해 주세요 :\n{json.dumps(posting, ensure_ascii=False)}
    """
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    try:
        response = requests.post(GEMINI_API_URL, params=params, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        summary = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '').strip()
        posting['summary'] = summary
    except Exception as e:
        posting['summary'] = f"[AI 요약 실패: {e}]"
    return posting


# read from rds postings with shorts url, get newest posting
def get_newest_posting_without_video():
    print("Connecting to the database...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        db=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4'
    )
    try:
        print("Connected to the database. Executing query...")
        with conn.cursor() as cur:
            sql = (
                "SELECT * FROM postings "
                "WHERE youtube_url IS NULL OR youtube_url = '' "
                "ORDER BY posting_id DESC LIMIT 1"
            )
            cur.execute(sql)
            print("Query executed successfully. Fetching result...")
            row = cur.fetchone()
            if row:
                print("Row fetched successfully. Converting to posting object...")
                return db_row_to_posting_object(cur, row)
            else:
                print("No rows found matching the criteria.")
                return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        print("Closing the database connection...")
        conn.close()
        print("Database connection closed.")


# Generates a detail page HTML string for a given posting object, using the same format as housing-1.html.
# If some data (like video url) are missing, it will display a placeholder message.
def generate_detail_page_html(posting, posting_types, save_local=True, save_s3=True, s3_bucket='wepl-posting-pages', s3_folder=None):
    """
    Generates a detail page HTML string for a given posting object, using the same format as housing-1.html.
    If some data (like video url) are missing, it will display a placeholder message.
    Also saves the HTML locally and to AWS S3 with the format {agency_id}-{posting_id}.html.
    """
    # Initialize main_content to hold the HTML content
    main_content = ""

    # Price formatting helper function
    def format_price(price_value):
        """Format price to 억/만원 units, or 없음 if 0"""
        if price_value is None or price_value == 0 or price_value == "0" or price_value == "0.0":
            return "없음"
        try:
            # Convert to float if it's a string
            if isinstance(price_value, str):
                price_float = float(price_value)
            else:
                price_float = float(price_value)
            
            if price_float >= 100_000_000:  # 1억 이상
                eok_decimal = price_float / 100_000_000
                return f"{eok_decimal:.1f}억원"
            else:  # 1억 미만
                man = int(round(price_float / 10_000))
                return f"{man:,}만원"
        except (ValueError, TypeError):
            return "없음"

    # Helper for safe value
    def safe(val, default="-"):
        return val if val not in (None, "") else default

    # Color scheme functions matching the JavaScript file exactly
    def get_supply_type_color(type_id):
        """Get consistent color scheme for supply type badges - matches JavaScript getSupplyTypeColor function"""
        try:
            type_id = int(type_id) if type_id else 1
        except (ValueError, TypeError):
            type_id = 1
            
        # These colors match exactly with the JavaScript getSupplyTypeColor function
        colors = {
            1: "bg-gray-100 text-gray-800 border-gray-300",      # 일반공급
            2: "bg-blue-100 text-blue-800 border-blue-300",      # 청년우선공급
            3: "bg-rose-100 text-rose-800 border-rose-300",      # 신혼부부우선공급
            4: "bg-orange-100 text-orange-800 border-orange-300", # 다자녀우선공급
            5: "bg-yellow-100 text-yellow-800 border-yellow-300", # 행복주택
            6: "bg-pink-100 text-pink-800 border-pink-300",      # 신혼신생아 전세임대
            7: "bg-amber-100 text-amber-800 border-amber-400"    # 든든전세
        }
        return colors.get(type_id, "bg-gray-100 text-gray-800 border-gray-300")

    def get_house_type_color(house_type):
        """Get consistent color scheme for house type badges - matches JavaScript getHouseTypeColor function"""
        # These colors match exactly with the JavaScript getHouseTypeColor function
        colors = {
            "아파트": "bg-sky-100 text-sky-800 border-sky-300",
            "연립주택": "bg-amber-100 text-amber-800 border-amber-300", 
            "다가구주택": "bg-lime-100 text-lime-800 border-lime-300",
            "단독주택": "bg-stone-100 text-stone-800 border-stone-300",
            "오피스텔(주거용)": "bg-purple-100 text-purple-800 border-purple-300",
            "다세대주택": "bg-lime-100 text-lime-800 border-lime-300"
        }
        return colors.get(house_type, "bg-gray-100 text-gray-800 border-gray-300")

    def get_status_info(apply_start, apply_end):
        """Get status info based on dates - matches JavaScript getStatusInfo function"""
        from datetime import datetime
        
        try:
            today = datetime.now().date()
            start_date = datetime.strptime(apply_start, '%Y-%m-%d').date() if apply_start and apply_start != "-" else None
            end_date = datetime.strptime(apply_end, '%Y-%m-%d').date() if apply_end and apply_end != "-" else None
            
            if start_date and end_date:
                if today < start_date:
                    # Before application start - 공고중 (light green)
                    return {
                        "status": "공고중",
                        "color": "bg-green-50 text-green-700 border-green-400"
                    }
                elif start_date <= today <= end_date:
                    # Within application period - 접수중 (bright green)
                    return {
                        "status": "접수중", 
                        "color": "bg-green-200 text-green-900 border-green-800"
                    }
                else:
                    # After application end - 종료 (red)
                    return {
                        "status": "종료",
                        "color": "bg-red-100 text-red-800 border-red-300"
                    }
            else:
                # Default status when dates are not available
                return {
                    "status": "공고중",
                    "color": "bg-green-50 text-green-700 border-green-400"
                }
        except (ValueError, TypeError):
            # Fallback for invalid dates
            return {
                "status": "공고중", 
                "color": "bg-green-50 text-green-700 border-green-400"
            }

    # Legacy function for backward compatibility - now uses getStatusInfo
    def get_status_color(status):
        """Legacy function - kept for compatibility"""
        return "bg-green-100 text-green-800 border-green-300" if status == "Y" else "bg-red-100 text-red-800 border-red-300"

    # Fetch posting type details
    posting_type_id = posting.get("posting_type_id")
    posting_type_details = posting_types.get(posting_type_id, {})

    # Debugging: Print posting_type_id and fetched posting_type_details
    print("Posting Type ID:", posting_type_id)
    print("Fetched Posting Type Details:", posting_type_details)

    # Ensure posting_type_id is correctly matched
    if not posting_type_details:
        print(f"No matching posting type found for posting_type_id: {posting_type_id}")

    # Correctly fetch limits from posting_type_details and format them
    income_limit = format_price(posting_type_details.get('salary_limit')) if posting_type_details.get('salary_limit') else '정보 없음'
    asset_limit = format_price(posting_type_details.get('asset_limit')) if posting_type_details.get('asset_limit') else '정보 없음'
    vehicle_limit = format_price(posting_type_details.get('vehicle_limit')) if posting_type_details.get('vehicle_limit') else '정보 없음'

    # Define application_status variable
    application_status = safe(posting.get('application_status'), '정보 없음')

    # Debugging: Print the correctly fetched values
    print("Correct values from posting_type_details:")
    print("Income Limit:", income_limit)
    print("Asset Limit:", asset_limit)
    print("Vehicle Limit:", vehicle_limit)

    # Video URL logic - Updated for proper 16:9 aspect ratio and shorter card when no video
    video_url = posting.get('youtube_url')
    if video_url:
        video_embed = f'''<div class="relative w-full" style="aspect-ratio: 16/9;">
            <iframe class="absolute inset-0 w-full h-full rounded-lg" src="{video_url}" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
        </div>'''
        video_card_padding = "p-4 pt-0"
    else:
        video_embed = '<div class="flex items-center justify-center w-full h-24 text-gray-400 text-lg bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">영상이 곧 제공될 예정입니다.</div>'
        video_card_padding = "p-4 pt-0"
    
    # AI summary logic
    ai_summary = posting.get('ai_summary') or 'AI 요약이 곧 제공될 예정입니다.'
    # Agency name
    agency_name = safe(posting.get('agency_id'), '기관 정보 없음')
    # Application URL
    application_url = safe(posting.get('application_url'), '#')
    # Dates
    apply_start = safe(posting.get('application_start'))
    apply_end = safe(posting.get('application_end'))
    # Price
    deposit = format_price(posting.get('deposit'))
    rent = format_price(posting.get('rent'))
    # Address
    area_province = safe(posting.get('area_province'))
    area_city = safe(posting.get('area_city'))
    address = safe(posting.get('address'))
    # Types
    building_type = safe(posting.get('building_type'))
    # Summary
    summary = safe(posting.get('summary'))
    if not summary:
        summary = posting.get('ai_summary')
    if not summary:
        summary = '요약 정보가 곧 제공될 예정입니다.'
    # Posting ID
    posting_id = safe(posting.get('posting_id'))
    # Posting type details
    posting_type_name = safe(posting_type_details.get('type_name'), 'Unknown Type')

    # Get color schemes using the updated functions that match JavaScript
    supply_type_color = get_supply_type_color(posting_type_id)
    house_type_color = get_house_type_color(building_type)
    
    # Get status info using the new function that matches JavaScript
    status_info = get_status_info(apply_start, apply_end)
    status = status_info["status"]
    status_color = status_info["color"]

    # make a full address for geocoding
    fullAddress = f"{area_province} {area_city} {address}".strip()

    # HTML
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{area_province} {area_city} {building_type} - 한눈에 공공임대</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="style.css">
    <!-- Kakao Maps API -->
    <script type="text/javascript" src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_API}&libraries=services"></script>
</head>
<body class="bg-gray-50">
    <header class="bg-white shadow-sm border-b">
        <div class="max-w-7xl mx-auto px-8 py-8">
            <div class="flex items-center gap-4">
                <a href="index.html" class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-transparent hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2">
                    목록으로
                </a>
                <div class="flex-1 flex items-center">
                    <div class="rounded-lg bg-white p-4">
                        <h1 class="text-3xl font-bold text-gray-900">
                            {area_province} {area_city} {building_type}
                        </h1>
                        <div class="flex items-center gap-2 mt-2">
                            <span id="status-badge" class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border {status_color}">
                                {status}
                            </span>
                            <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border {supply_type_color}">
                                {posting_type_name}
                            </span>
                            <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border {house_type_color}">
                                {building_type}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </header>
    <div class="max-w-7xl mx-auto px-8 py-8">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="lg:col-span-2 space-y-6">
                <div class="rounded-lg border border-gray-300 bg-white text-card-foreground shadow-sm">
                    <div class="flex flex-col space-y-1.5 p-6 pb-4">
                        <h3 class="text-2xl font-semibold leading-none tracking-tight flex items-center gap-2">
                            기본 정보
                        </h3>
                    </div>
                    <div class="p-6 pt-2 space-y-4">
                        <div class="mb-4">
                            <span class="inline-flex items-center rounded-xl px-6 py-4 text-lg font-semibold border bg-blue-50 text-blue-900 border-blue-200 w-full block text-center">
                                {summary}
                            </span>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div class="flex items-center gap-2">
                                <span class="font-medium">공고번호:</span>
                                <span>{posting_id}</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <span class="font-medium">상태:</span>
                                <span id="status-badge-2" class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border {status_color}">
                                    {status}
                                </span>
                            </div>
                            <div class="flex items-center gap-2">
                                <span class="font-medium">공급유형:</span>
                                <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border {supply_type_color}">
                                    {posting_type_name}
                                </span>
                            </div>
                            <div class="flex items-center gap-2">
                                <span class="font-medium">상세주소:</span>
                                <span>{address}</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <span class="font-medium">신청시작일:</span>
                                <span>{apply_start}</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <span class="font-medium">신청마감일:</span>
                                <span>{apply_end}</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <span class="font-medium">주택유형:</span>
                                <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border {house_type_color}">
                                    {building_type}
                                </span>
                            </div>
                            <div class="flex items-center gap-2">
                                <span class="font-medium">주관기관:</span>
                                <span>{agency_name}</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- AI Summary Video -->
                <div class="rounded-lg border border-gray-300 bg-white text-card-foreground shadow-sm">
                    <div class="flex flex-col space-y-1.5 p-4">
                        <h3 class="text-2xl font-semibold leading-none tracking-tight flex items-center gap-2">
                            AI 요약
                        </h3>
                    </div>
                    <div class="{video_card_padding}">
                        {video_embed}
                    </div>
                </div>

                <!-- Eligibility Requirements -->
                <div class="rounded-lg border border-gray-300 bg-white text-card-foreground shadow-sm">
                    <div class="flex flex-col space-y-1.5 p-6 pb-4">
                        <h3 class="text-2xl font-semibold leading-none tracking-tight">자격 요건</h3>
                    </div>
                    <div class="p-6 pt-2">
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div class="text-center p-4 bg-gray-50 rounded-lg">
                                <p class="text-sm text-gray-600 mb-2">월 소득 한도</p>
                                <p class="text-xl font-bold text-gray-800">{income_limit}</p>
                            </div>
                            <div class="text-center p-4 bg-gray-50 rounded-lg">
                                <p class="text-sm text-gray-600 mb-2">총 자산 한도</p>
                                <p class="text-xl font-bold text-gray-800">{asset_limit}</p>
                            </div>
                            <div class="text-center p-4 bg-gray-50 rounded-lg">
                                <p class="text-sm text-gray-600 mb-2">차량가액 한도</p>
                                <p class="text-xl font-bold text-gray-800">{vehicle_limit}</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Application Information -->
                <div class="rounded-lg border border-gray-300 bg-white text-card-foreground shadow-sm">
                    <div class="flex flex-col space-y-1.5 p-6 pb-4">
                        <h3 class="text-2xl font-semibold leading-none tracking-tight flex items-center gap-2">
                            신청 정보
                        </h3>
                    </div>
                    <div class="p-6 pt-2">
                        <div class="space-y-4">
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <span class="font-medium text-gray-700">신청 기간</span>
                                    <p class="text-lg font-semibold text-gray-900">
                                        {apply_start} ~ {apply_end}
                                    </p>
                                </div>
                                <div>
                                    <span class="font-medium text-gray-700">신청 상태</span>
                                    <p id="app-status-text" class="text-lg font-semibold text-green-600">
                                        {status}
                                    </p>
                                </div>
                            </div>
                            <div class="pt-4 border-t">
                                <span class="font-medium text-gray-700">신청 웹사이트</span>
                                <div class="mt-2">
                                    <a href="{application_url}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 underline break-all text-lg">
                                        {application_url}
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="space-y-6">
                <!-- Rent Price Information (moved to top of right sidebar) -->
                <div class="rounded-lg border border-gray-300 bg-white text-card-foreground shadow-sm">
                    <div class="flex flex-col space-y-1.5 p-6 pb-4">
                        <h3 class="text-2xl font-semibold leading-none tracking-tight">임대료 정보</h3>
                    </div>
                    <div class="p-6 pt-2">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div class="text-center p-6 bg-gray-200 rounded-lg border-2 border-gray-500">
                                <p class="text-sm text-gray-700 mb-2">보증금</p>
                                <p class="text-3xl font-bold text-gray-900">{deposit}</p>
                            </div>
                            <div class="text-center p-6 bg-gray-50 rounded-lg border-2 border-gray-400">
                                <p class="text-sm text-gray-700 mb-2">월세</p>
                                <p class="text-3xl font-bold">{rent}</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Application Button (moved above map) -->
                <div class="rounded-lg border border-gray-300 bg-white text-card-foreground shadow-sm">
                    <div class="p-6">
                        <a href="{application_url}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-lg font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-black text-white hover:bg-gray-800 h-auto flex flex-col py-4 px-4 min-h-[80px] w-full mb-4">
                            <div class="flex items-center gap-2 mb-2">
                                <span class="font-semibold">신청하기</span>
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-external-link"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>
                            </div>
                            <span class="text-sm opacity-90 leading-tight text-center">
                                {agency_name}
                            </span>
                        </a>
                        <p class="text-sm text-gray-600 text-center">신청 마감: {apply_end}</p>
                    </div>
                </div>

                <!-- Location Map (now below the apply button) -->
                <div class="rounded-lg border border-gray-300 bg-white text-card-foreground shadow-sm">
                    <div class="flex flex-col space-y-1.5 p-6 pb-4">
                        <h3 class="text-2xl font-semibold leading-none tracking-tight flex items-center gap-2">
                            위치 정보
                        </h3>
                    </div>
                    <div class="p-6 pt-2">
                        <div class="space-y-3">
                            <div id="map" class="w-full h-60 rounded-lg border overflow-hidden bg-gray-100"></div>
                            <div class="text-sm text-gray-600 text-center">
                                {address}
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    </div>

    <script src="script.js"></script>
    <script>
        // Update application status based on current date using the same logic as the main site
        function updateApplicationStatus() {{
            const today = new Date();
            const applicationStart = new Date('{apply_start}');
            const applicationEnd = new Date('{apply_end}');
            
            let statusInfo = getStatusInfo('{apply_start}', '{apply_end}');
            
            // Update all status badges
            const statusBadges = ['status-badge', 'status-badge-2', 'status-badge-3'];
            statusBadges.forEach(id => {{
                const badge = document.getElementById(id);
                if (badge) {{
                    badge.textContent = statusInfo.status;
                    badge.className = `inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${{statusInfo.color}}`;
                }}
            }});
            
            // Also update in application information section
            const appStatusElement = document.getElementById('app-status-text');
            if (appStatusElement) {{
                let appStatusText = '';
                let appStatusColor = '';
                if (today < new Date('{apply_start}')) {{
                    appStatusText = '신청 접수 예정';
                    appStatusColor = 'text-gray-600';
                }} else if (today >= new Date('{apply_start}') && today <= new Date('{apply_end}')) {{
                    appStatusText = '현재 신청 접수 중';
                    appStatusColor = 'text-green-600';
                }} else {{
                    appStatusText = '신청 접수 종료';
                    appStatusColor = 'text-red-600';
                }}
                appStatusElement.textContent = appStatusText;
                appStatusElement.className = `text-lg font-semibold ${{appStatusColor}}`;
            }}
        }}
        
        // Use the same getStatusInfo function from script.js
        function getStatusInfo(applyStart, applyEnd) {{
            const today = new Date();
            const startDate = new Date(applyStart);
            const endDate = new Date(applyEnd);
            
            if (today < startDate) {{
                return {{
                    status: "공고중",
                    color: "bg-green-50 text-green-700 border-green-400"
                }};
            }} else if (today >= startDate && today <= endDate) {{
                return {{
                    status: "접수중", 
                    color: "bg-green-200 text-green-900 border-green-800"
                }};
            }} else {{
                return {{
                    status: "종료",
                    color: "bg-red-100 text-red-800 border-red-300"
                }};
            }}
        }}
        
        // Run on page load
        document.addEventListener('DOMContentLoaded', function() {{
            updateApplicationStatus();
            
            // Initialize map after a short delay to ensure DOM is ready
            setTimeout(function() {{
                if (typeof kakao !== 'undefined' && kakao.maps) {{
                    initDetailPageMap();
                }} else {{
                    console.error('Kakao Maps API not loaded');
                }}
            }}, 100);
        }});
    </script>
</body>
</html>'''
    
    # Save locally
    filename = f"{agency_name}-{posting_id}.html"
    if save_local:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
    
    # Save to S3
    if save_s3:
        try:
            s3 = boto3.client('s3')
            s3_key = f"{s3_folder}/{filename}" if s3_folder else filename
            
            # Upload HTML content directly to S3
            s3.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=html.encode('utf-8'),
                ContentType='text/html; charset=utf-8',
                ContentEncoding='utf-8'
            )
            print(f"Uploaded detail page {filename} to S3 bucket {s3_bucket}/{s3_key}")
        except Exception as e:
            print(f"Error uploading detail page to S3: {e}")
    
    return html





# Converts a DB row to a posting object (dict) for Gemini API or other use.
def db_row_to_posting_object(cur, row):
    # Get column names from cursor description
    columns = [desc[0] for desc in cur.description]
    posting = dict(zip(columns, row))
    # Convert to uniform, JSON-serializable format
    return make_json_serializable(posting)

def fetch_all_posting_types():
    """
    Fetches all posting types from the database and returns them as a dictionary.
    """
    print("Fetching all posting types from the database...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        db=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4'
    )
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            sql = "SELECT * FROM posting_type"
            cur.execute(sql)
            print("Query executed successfully. Fetching all posting types...")
            rows = cur.fetchall()
            # Convert rows to a dictionary with posting_type_id as the key
            posting_types = {row["posting_type_id"]: row for row in rows}
            print("Posting types fetched successfully.")
            return posting_types
    except Exception as e:
        print(f"An error occurred while fetching posting types: {e}")
        return {}
    finally:
        print("Closing the database connection...")
        conn.close()
        print("Database connection closed.")

# Main function to fetch and print the number of postings from HUG and LH APIs.
def main():


    
    
    
    # Query DB for oldest posting without video URL and print it
    newest_posting = get_newest_posting_without_video()
    print("\nnewest posting without video URL:")
    print(newest_posting)

    # Test sending to Gemini AI and print the response
    if newest_posting:
        ai_posting = get_ai_summary_for_posting(newest_posting)
        print("\nAI summary response:")
        print(ai_posting.get('ai_summary'))

    else:
        print("No posting found without video URL.")

    # Print the result of fetch_all_posting_types
    posting_types = fetch_all_posting_types()
    print("Fetched posting types:", posting_types)

    # Test the generate_detail_page_html function using the newest posting without video URL
    newest_posting = get_newest_posting_without_video()
    if newest_posting:
        print("Generating detail page HTML for the newest posting...")
        html_output = generate_detail_page_html(newest_posting, posting_types, save_local=True, save_s3=True)
        print("Detail page HTML generated successfully for the newest posting.")
    else:
        print("No posting found without video URL to generate detail page.")


def append_posting_to_index_html(posting, posting_types, html_file_path="index.html"):
    """
    Appends a new posting object to the main HTML page by adding it to the embedded data section.
    
    Args:
        posting: Dictionary containing posting data
        posting_types: Dictionary of posting types for lookups
        html_file_path: Path to the HTML file (default: "index.html")
    """
    try:
        # Read the existing HTML file
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Helper function to safely get values
        def safe_value(val, default=""):
            return str(val) if val not in (None, "") else default
        
        # Extract posting data with safe defaults
        notice_id = safe_value(posting.get('posting_id'))
        status = "Y" if posting.get('summary') != '종료' else "N"  # Y for active, N for ended
        region_province = safe_value(posting.get('area_province'))
        region_city = safe_value(posting.get('area_city'))
        address_detail = safe_value(posting.get('address'))
        apply_start = safe_value(posting.get('application_start'))
        apply_end = safe_value(posting.get('application_end'))
        house_type = safe_value(posting.get('building_type'))
        supply_type_id = safe_value(posting.get('posting_type_id'), "1")
        application_url = safe_value(posting.get('application_url'))
        deposit = safe_value(posting.get('deposit'), "0")
        monthly_rent = safe_value(posting.get('rent'), "0")
        agency_id = safe_value(posting.get('agency_id'))
        
        # Get posting type details for limits
        posting_type_details = posting_types.get(posting.get('posting_type_id'), {})
        income_limit = safe_value(posting_type_details.get('salary_limit'), "0")
        asset_limit = safe_value(posting_type_details.get('asset_limit'), "0")
        vehicle_limit = safe_value(posting_type_details.get('vehicle_limit'), "0")
        
        # Convert limits from raw numbers to 만원 units (divide by 10000)
        try:
            income_limit = str(int(float(income_limit) / 10000)) if income_limit != "0" else "0"
            asset_limit = str(int(float(asset_limit) / 10000)) if asset_limit != "0" else "0"
            vehicle_limit = str(int(float(vehicle_limit) / 10000)) if vehicle_limit != "0" else "0"
        except (ValueError, TypeError):
            income_limit = asset_limit = vehicle_limit = "0"
        
        # Create the new housing item HTML
        new_housing_item = f'''        <div class="housing-item"
             data-notice_id="{notice_id}"
             data-status="{status}"
             data-region_province="{region_province}"
             data-region_city="{region_city}"
             data-address_detail="{address_detail}"
             data-apply_start="{apply_start}"
             data-apply_end="{apply_end}"
             data-house_type="{house_type}"
             data-supply_type_id="{supply_type_id}"
             data-application_url="{application_url}"
             data-deposit="{deposit}"
             data-monthly_rent="{monthly_rent}"
             data-agency_id="{agency_id}"
             data-income_limit="{income_limit}"
             data-asset_limit="{asset_limit}"
             data-vehicle_limit="{vehicle_limit}">
        </div>'''
        
        # Find the closing tag of the housing-data div
        housing_data_end = html_content.find('    </div>\n\n    <script src="script.js">')
        
        if housing_data_end == -1:
            print("Error: Could not find the housing-data section end marker")
            return False
        
        # Insert the new housing item before the closing div
        updated_html = (
            html_content[:housing_data_end] + 
            new_housing_item + '\n' +
            html_content[housing_data_end:]
        )
        
        # Write the updated HTML back to the file
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(updated_html)
        print(f"✅ Successfully appended posting {notice_id} to {html_file_path}")
        # Upload updated main page to S3
        try:
            s3 = boto3.client('s3')
            s3.upload_file(html_file_path, 'wepl-mainpage', os.path.basename(html_file_path), ExtraArgs={'ContentType': 'text/html; charset=utf-8'})
            print(f"Uploaded {html_file_path} to S3 bucket wepl-mainpage")
        except Exception as e:
            print(f"Error uploading main page to S3: {e}")
        return True
    except Exception as e:
        print(f"❌ Error appending posting to HTML file: {e}")
        return False

def populate_index_html_with_all_postings(html_file_path="index.html"):
    """
    Reads all posting entries from the database and writes them to the index.html file's embedded data section.
    This replaces all existing housing-item divs with fresh data from the database.
    
    Args:
        html_file_path: Path to the HTML file (default: "index.html")
    """
    try:
        # Fetch all postings from database
        print("Connecting to database to fetch all postings...")
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            db=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            charset='utf8mb4'
        )
        
        postings = []
        posting_types = {}
        
        try:
            # Fetch all posting types for lookup
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute("SELECT * FROM posting_type")
                posting_type_rows = cur.fetchall()
                posting_types = {row["posting_type_id"]: row for row in posting_type_rows}
            
            # Fetch all postings
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute("SELECT * FROM postings ORDER BY posting_id DESC")
                posting_rows = cur.fetchall()
                postings = [make_json_serializable(row) for row in posting_rows]
                
            print(f"✅ Fetched {len(postings)} postings and {len(posting_types)} posting types from database")
            
        finally:
            conn.close()
        
        # Read the existing HTML file
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Helper function to safely get values
        def safe_value(val, default=""):
            return str(val) if val not in (None, "") else default
        
        # Build all housing items HTML
        housing_items_html = ""
        
        for posting in postings:
            # Extract posting data with safe defaults
            notice_id = safe_value(posting.get('posting_id'))
            
            # Determine status based on application dates
            today = datetime.date.today()
            status = "Y"  # Default to active
            
            import datetime

            try:
                apply_start_str = str(posting.get('application_start'))
                apply_end_str = str(posting.get('application_end'))

                if apply_start_str and apply_end_str and apply_start_str != 'None' and apply_end_str != 'None':
                    apply_start = datetime.datetime.strptime(apply_start_str, '%Y-%m-%d').date()
                    apply_end = datetime.datetime.strptime(apply_end_str, '%Y-%m-%d').date()

                    # Status logic: Y for active (공고중/접수중), N for ended (종료)
                    if datetime.date.today() <= apply_end:
                        status = "Y"
                    else:
                        status = "N"
            except (ValueError, TypeError):
                # If date parsing fails, default to active
                status = "Y"

            
            # Extract other fields
            region_province = safe_value(posting.get('area_province'))
            region_city = safe_value(posting.get('area_city'))
            address_detail = safe_value(posting.get('address'))
            apply_start = safe_value(posting.get('application_start'))
            apply_end = safe_value(posting.get('application_end'))
            house_type = safe_value(posting.get('building_type'))
            supply_type_id = safe_value(posting.get('posting_type_id'), "1")
            application_url = safe_value(posting.get('application_url'))
            deposit = safe_value(posting.get('deposit'), "0")
            monthly_rent = safe_value(posting.get('rent'), "0")
            agency_id = safe_value(posting.get('agency_id'))
            
            # Get posting type details for limits
            posting_type_details = posting_types.get(posting.get('posting_type_id'), {})
            income_limit = safe_value(posting_type_details.get('salary_limit'), "0")
            asset_limit = safe_value(posting_type_details.get('asset_limit'), "0")
            vehicle_limit = safe_value(posting_type_details.get('vehicle_limit'), "0")
            
            # Convert limits from raw numbers to 만원 units (divide by 10000)
            try:
                income_limit = str(int(float(income_limit) / 10000)) if income_limit != "0" else "0"
                asset_limit = str(int(float(asset_limit) / 10000)) if asset_limit != "0" else "0"
                vehicle_limit = str(int(float(vehicle_limit) / 10000)) if vehicle_limit != "0" else "0"
            except (ValueError, TypeError):
                income_limit = asset_limit = vehicle_limit = "0"
            
            # Create the housing item HTML
            housing_item = f'''        <div class="housing-item"
             data-notice_id="{notice_id}"
             data-status="{status}"
             data-region_province="{region_province}"
             data-region_city="{region_city}"
             data-address_detail="{address_detail}"
             data-apply_start="{apply_start}"
             data-apply_end="{apply_end}"
             data-house_type="{house_type}"
             data-supply_type_id="{supply_type_id}"
             data-application_url="{application_url}"
             data-deposit="{deposit}"
             data-monthly_rent="{monthly_rent}"
             data-agency_id="{agency_id}"
             data-income_limit="{income_limit}"
             data-asset_limit="{asset_limit}"
             data-vehicle_limit="{vehicle_limit}">
        </div>'''
            
            housing_items_html += housing_item + '\n'
        
        # Find the housing-data section boundaries
        housing_data_start = html_content.find('<div id="housing-data" class="hidden">')
        housing_data_end = html_content.find('    </div>\n\n    <script src="script.js">')
        
        if housing_data_start == -1 or housing_data_end == -1:
            print("❌ Error: Could not find the housing-data section boundaries")
            return False
        
        # Find the end of the opening div tag
        opening_tag_end = html_content.find('>', housing_data_start) + 1
        
        # Replace the content between the housing-data div tags
        updated_html = (
            html_content[:opening_tag_end] + '\n' +
            housing_items_html +
            html_content[housing_data_end:]
        )
        
        # Write the updated HTML back to the file
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(updated_html)
        print(f"✅ Successfully populated {html_file_path} with {len(postings)} postings from database")
        # Upload updated main page to S3
        try:
            s3 = boto3.client('s3')
            s3.upload_file(html_file_path, 'wepl-mainpage', os.path.basename(html_file_path), ExtraArgs={'ContentType': 'text/html; charset=utf-8'})
            print(f"Uploaded {html_file_path} to S3 bucket wepl-mainpage")
        except Exception as e:
            print(f"Error uploading main page to S3: {e}")
        return True
    except Exception as e:
        print(f"❌ Error populating HTML file with database postings: {e}")
        return False

def sync_all_postings_to_html(html_file_path="index.html"):
    """
    Syncs all postings from the database to index.html by replacing the housing-data section,
    and uploads the updated index.html to the 'wepl-mainpage' S3 bucket.
    """
    # Fetch postings and posting types
    print("Starting database to HTML sync...")
    try:
        conn = pymysql.connect(
            host=DB_HOST, port=DB_PORT, db=DB_NAME,
            user=DB_USER, password=DB_PASSWORD, charset='utf8mb4'
        )
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("SELECT * FROM posting_type")
            posting_types = {row['posting_type_id']: row for row in cur.fetchall()}
            cur.execute("SELECT * FROM postings ORDER BY posting_id DESC")
            postings = [make_json_serializable(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"Error fetching data from database: {e}")
        return False
    finally:
        conn.close()

    if not postings:
        print("No postings found in database to sync.")
        return False

    # Read existing index.html
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"Error reading {html_file_path}: {e}")
        return False

    # Helper function for safe value handling
    def safe_value(val, default=""):
        return str(val) if val not in (None, "") else default

    # Build housing items
    items_html = []
    for p in postings:
        # Determine status
        status = 'Y'
        try:
            if p.get('application_end'):
                end_date = datetime.datetime.fromisoformat(str(p['application_end'])).date()
                if datetime.date.today() > end_date:
                    status = 'N'
        except Exception as e:
            print(f"Error determining status: {e}")
            pass

        # Get posting type details and format limits
        posting_type = posting_types.get(p.get('posting_type_id'), {})
        income_limit = '0'
        asset_limit = '0'
        vehicle_limit = '0'

        try:
            if posting_type.get('salary_limit'):
                income_limit = str(int(float(posting_type['salary_limit']) / 10000))
            if posting_type.get('asset_limit'):
                asset_limit = str(int(float(posting_type['asset_limit']) / 10000))
            if posting_type.get('vehicle_limit'):
                vehicle_limit = str(int(float(posting_type['vehicle_limit']) / 10000))
        except (ValueError, TypeError) as e:
            print(f"Error formatting limits: {e}")

        # Generate housing item div
        item_div = f'''        <div class="housing-item"
             data-notice_id="{safe_value(p.get('posting_id'))}"
             data-status="{status}"
             data-region_province="{safe_value(p.get('area_province'))}"
             data-region_city="{safe_value(p.get('area_city'))}"
             data-address_detail="{safe_value(p.get('address'))}"
             data-apply_start="{safe_value(p.get('application_start'))}"
             data-apply_end="{safe_value(p.get('application_end'))}"
             data-house_type="{safe_value(p.get('building_type'))}"
             data-supply_type_id="{safe_value(p.get('posting_type_id'), '1')}"
             data-application_url="{safe_value(p.get('application_url'))}"
             data-deposit="{safe_value(p.get('deposit'), '0')}"
             data-monthly_rent="{safe_value(p.get('rent'), '0')}"
             data-agency_id="{safe_value(p.get('agency_id'))}"
             data-income_limit="{income_limit}"
             data-asset_limit="{asset_limit}"
             data-vehicle_limit="{vehicle_limit}">
        </div>'''
        items_html.append(item_div)

    # Find the housing-data section boundaries
    housing_data_start = html_content.find('<div id="housing-data" class="hidden">')
    housing_data_end = html_content.find('    </div>\n\n    <script src="script.js">')
    
    if housing_data_start == -1 or housing_data_end == -1:
        print("Error: Could not find housing-data section markers in HTML file")
        return False
    
    # Find the end of the opening div tag
    opening_tag_end = html_content.find('>', housing_data_start) + 1
    
    # Replace the content between the housing-data div tags
    updated_html = (
        html_content[:opening_tag_end] + '\n' +
        '\n'.join(items_html) + '\n' +
        html_content[housing_data_end:]
    )
    
    # Write the updated HTML back to the file
    try:
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(updated_html)
        print(f"✅ Successfully synced {len(postings)} postings to {html_file_path}")
    except Exception as e:
        print(f"Error writing HTML file: {e}")
        return False
    
    # Upload updated main page to S3
    try:
        s3 = boto3.client('s3')
        s3.upload_file(html_file_path, 'wepl-mainpage', os.path.basename(html_file_path), 
                      ExtraArgs={'ContentType': 'text/html; charset=utf-8'})
        print(f"✅ Uploaded {html_file_path} to S3 bucket wepl-mainpage")
    except Exception as e:
        print(f"⚠️  Could not upload to S3: {e}")
    
    return True


def check_pub_api():
    """Check the public APIs for connectivity and data availability"""
    print("🔍 Checking public API connectivity...")
    
    # Check HUG API
    try:
        response = requests.get(api_url_hug, timeout=10)
        response.raise_for_status()
        hug_data = response.json()
        hug_count = len(hug_data.get('response', {}).get('body', {}).get('item', []))
        print(f"✅ HUG API: Connected successfully, {hug_count} items available")
    except Exception as e:
        print(f"❌ HUG API: Failed to connect - {e}")
    
    # Check LH API
    try:
        response = requests.get(api_url_lh, timeout=10)
        response.raise_for_status()
        lh_data = response.json()
        lh_items = lh_data.get('response', {}).get('body', {}).get('item', [])
        if not isinstance(lh_items, list):
            lh_items = [lh_items]
        print(f"✅ LH API: Connected successfully, {len(lh_items)} items available")
    except Exception as e:
        print(f"❌ LH API: Failed to connect - {e}")


def is_lambda_environment():
    """Check if we're running in AWS Lambda environment"""
    return os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None


def complete_lh_workflow(save_local=False, save_s3=True):
    """
    Complete LH workflow: fetch data, process, save to DB, generate pages, sync index.
    Now works with improved Secrets Manager integration.
    """
    print("🚀 Starting complete LH workflow...")
    
    try:
        # Step 1: Fetch LH API data
        print("\n📡 Step 1: Fetching LH API data...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            lh_data_raw = loop.run_until_complete(get_lh_api())
        finally:
            loop.close()
        
        if not lh_data_raw:
            print("❌ No data from LH API")
            return {'success': False, 'error': 'No LH API data'}
        
        print(f"✅ Fetched {len(lh_data_raw)} items from LH API")
        
        # Step 2: Extract and structure fields
        print("\n🔧 Step 2: Processing LH data...")
        extracted_data = extract_lh_fields({'response': {'body': {'item': lh_data_raw}}})
        
        if not extracted_data:
            print("❌ No data extracted from LH response")
            return {'success': False, 'error': 'No extracted data'}
        
        print(f"✅ Extracted {len(extracted_data)} structured postings")
        
        # Step 3: Filter new postings
        print("\n🔍 Step 3: Filtering new postings...")
        new_postings = filter_new_postings(extracted_data)
        print(f"✅ Found {len(new_postings)} new postings to process")
        
        if not new_postings:
            print("ℹ️  No new postings to process")
            return {'success': True, 'new_postings': 0, 'message': 'No new postings found'}
        
        # Step 4: Save new postings to database
        print(f"\n💾 Step 4: Saving {len(new_postings)} postings to database...")
        saved_count = 0
        for posting in new_postings:
            try:
                save_posting_to_db(posting)
                saved_count += 1
            except Exception as e:
                print(f"❌ Failed to save posting {posting.get('posting_id')}: {e}")
        
        print(f"✅ Saved {saved_count}/{len(new_postings)} postings to database")
        
        # Step 5: Generate detail pages for new postings
        if saved_count > 0:
            print(f"\n📄 Step 5: Generating detail pages...")
            posting_types = fetch_all_posting_types()
            pages_generated = 0
            
            for posting in new_postings:
                try:
                    # Convert to proper posting object format
                    posting_obj = convert_to_posting_object(posting)
                    generate_detail_page_html(posting_obj, posting_types, 
                                            save_local=save_local, save_s3=save_s3)
                    pages_generated += 1
                except Exception as e:
                    print(f"❌ Failed to generate page for posting {posting.get('posting_id')}: {e}")
            
            print(f"✅ Generated {pages_generated} detail pages")
        
        # Step 6: Sync index.html with database
        print("\n🔄 Step 6: Syncing index.html with database...")
        sync_success = sync_all_postings_to_html()
        
        if sync_success:
            print("✅ Successfully synced index.html with database")
        else:
            print("⚠️  Index sync completed with warnings")
        
        print(f"\n🎉 LH workflow completed successfully!")
        print(f"   • New postings processed: {saved_count}")
        print(f"   • Detail pages generated: {pages_generated if saved_count > 0 else 0}")
        print(f"   • Index sync: {'Success' if sync_success else 'Warning'}")
        
        return {
            'success': True,
            'new_postings': saved_count,
            'detail_pages_generated': pages_generated if saved_count > 0 else 0,
            'index_synced': sync_success
        }
        
    except Exception as e:
        print(f"❌ LH workflow failed: {e}")
        return {'success': False, 'error': str(e)}


def convert_to_posting_object(extracted_posting):
    """Convert extracted posting data to standard posting object format"""
    return {
        'posting_id': extracted_posting.get('posting_id'),
        'posting_type_id': 1,  # Default to LH general type
        'agency_id': '1',  # LH agency
        'area_province': extracted_posting.get('prefecture'),
        'area_city': extracted_posting.get('city'),
        'address': extracted_posting.get('detailed_address'),
        'application_start': extracted_posting.get('application_start_date'),
        'application_end': extracted_posting.get('application_end_date'),
        'building_type': extracted_posting.get('building_type'),
        'application_url': extracted_posting.get('application_url'),
        'deposit': extracted_posting.get('deposit'),
        'rent': extracted_posting.get('rent'),
        'summary': extracted_posting.get('posting_summary', ''),
        'rawjson': json.dumps(extracted_posting, ensure_ascii=False),
        's3_object_address': None,
        'youtube_url': None
    }


def save_posting_to_db(posting):
    """Save a single posting object to the database"""
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT, db=DB_NAME,
        user=DB_USER, password=DB_PASSWORD, charset='utf8mb4'
    )
    
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO postings 
                (posting_id, posting_type_id, agency_id, area_province, area_city, 
                 address, application_start, application_end, building_type, 
                 application_url, deposit, rent, summary, rawjson)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                application_end = VALUES(application_end),
                deposit = VALUES(deposit),
                rent = VALUES(rent),
                summary = VALUES(summary),
                rawjson = VALUES(rawjson)
            """
            
            values = (
                posting.get('posting_id'),
                1,  # Default posting_type_id for LH
                '1',  # agency_id for LH
                posting.get('prefecture'),
                posting.get('city'),
                posting.get('detailed_address'),
                posting.get('application_start_date'),
                posting.get('application_end_date'),
                posting.get('building_type'),
                posting.get('application_url'),
                float(posting.get('deposit')) if posting.get('deposit') else None,
                float(posting.get('rent')) if posting.get('rent') else None,
                posting.get('posting_summary', ''),
                json.dumps(posting, ensure_ascii=False)
            )
            
            cur.execute(sql, values)
        conn.commit()
        
    finally:
        conn.close()


# Lambda handler function
def lambda_handler(event, context):
    """
    AWS Lambda handler function that can be triggered by various events.
    Supports different operations based on the 'action' parameter in the event.
    """
    print(f"🚀 Lambda function started in {os.environ.get('AWS_REGION', 'unknown')} region")
    
    try:
        # Get action from event, default to 'complete_workflow'
        action = event.get('action', 'complete_workflow')
        
        if action == 'complete_workflow':
            result = complete_lh_workflow(save_local=False, save_s3=True)
            
        elif action == 'sync_index':
            result = {'success': sync_all_postings_to_html()}
            
        elif action == 'check_apis':
            check_pub_api()
            result = {'success': True, 'message': 'API check completed'}
            
        elif action == 'update_recent_pages':
            days = event.get('days', 7)
            result = update_recent_detail_pages(days=days, save_local=False, save_s3=True)
            
        else:
            result = {'success': False, 'error': f'Unknown action: {action}'}
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"❌ Lambda function error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False)
        }
        item_div = f'''        <div class="housing-item"
             data-notice_id="{safe_value(p.get('posting_id'))}"
             data-status="{status}"
             data-region_province="{safe_value(p.get('area_province'))}"
             data-region_city="{safe_value(p.get('area_city'))}"
             data-address_detail="{safe_value(p.get('address'))}"
             data-apply_start="{safe_value(p.get('application_start'))}"
             data-apply_end="{safe_value(p.get('application_end'))}"
             data-house_type="{safe_value(p.get('building_type'))}"
             data-supply_type_id="{safe_value(p.get('posting_type_id'), '1')}"
             data-application_url="{safe_value(p.get('application_url'))}"
             data-deposit="{safe_value(p.get('deposit'), '0')}"
             data-monthly_rent="{safe_value(p.get('rent'), '0')}"
             data-agency_id="{safe_value(p.get('agency_id'))}"
             data-income_limit="{income_limit}"
             data-asset_limit="{asset_limit}"
             data-vehicle_limit="{vehicle_limit}">
        </div>'''
        items_html.append(item_div)

    # Replace housing-data section in HTML
    housing_data_start = html_content.find('<div id="housing-data" class="hidden">')
    housing_data_end = html_content.find('    </div>\n\n    <script src="script.js">')
    
    if housing_data_start == -1 or housing_data_end == -1:
        print("❌ Error: Could not find the housing-data section in HTML")
        return False

    opening_tag_end = html_content.find('>', housing_data_start) + 1
    updated_html = (
        html_content[:opening_tag_end] + '\n' +
        '\n'.join(items_html) +  # Fixed: Changed items_html.join('\n') to '\n'.join(items_html)
        html_content[housing_data_end:]
    )

    # Write and upload
    try:
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(updated_html)
        
        s3 = boto3.client('s3')
        s3.upload_file(
            html_file_path, 
            'wepl-mainpage', 
            os.path.basename(html_file_path), 
            ExtraArgs={'ContentType': 'text/html; charset=utf-8'}
        )
        print(f"✅ Successfully uploaded {html_file_path} to S3 bucket wepl-mainpage")
        return True
    except Exception as e:
        print(f"❌ Error saving or uploading file: {e}")
        return False

def check_pub_api():
    """
    Complete workflow to check public API for new postings, add AI summaries,
    generate detail pages, write to database, and update main HTML page.
    """
    print("🚀 Starting public API check workflow...")

    try:
        # Step 1: Get all postings from public API
        print("📡 Fetching postings from LH API...")
        lh_data = asyncio.run(get_lh_api())
        if not lh_data:
            print("❌ No data received from LH API")
            return False

        # Extract and format LH fields into posting objects
        lh_postings = extract_lh_fields({'response': {'body': {'item': lh_data}}})
        print(f"✅ Extracted {len(lh_postings)} postings from LH API")

        # Step 2: Filter for new postings (not already in database)
        print("🔍 Filtering for new postings...")
        new_postings = filter_new_postings(lh_postings)

        if not new_postings:
            print("✅ No new postings found. Database is up to date.")
            return True

        print(f"🆕 Found {len(new_postings)} new postings to process")
        
        # Step 3: Process each new posting (add AI summaries)
        summarized_postings = []  # Initialize the list
        
        for i, posting in enumerate(new_postings, 1):  # Add the missing for loop
            print(f"   Processing posting {i}/{len(new_postings)}: {posting.get('posting_id')}")
            try:
                # Convert LH format to standard posting format
                standardized_posting = {
                    'posting_id': posting.get('posting_id'),
                    'posting_type_id': 1,  # Default to LH type
                    'agency_id': 'LH',
                    'area_province': posting.get('prefecture'),
                    'area_city': posting.get('city'),
                    'address': posting.get('detailed_address'),
                    'application_start': posting.get('application_start_date'),
                    'application_end': posting.get('application_end_date'),
                    'building_type': posting.get('building_type'),
                    'application_url': posting.get('application_url'),
                    'deposit': posting.get('deposit'),
                    'rent': posting.get('rent'),
                    'summary': posting.get('posting_summary', ''),
                    'rawjson': json.dumps(posting, ensure_ascii=False),
                    's3_object_address': None,
                    'youtube_url': None
                }

                # Generate AI summary
                posting_with_summary = get_ai_summary_for_posting(standardized_posting)
                summarized_postings.append(posting_with_summary)
                print(f"   ✅ AI summary generated: {posting_with_summary.get('ai_summary', '')[:50]}...")

            except Exception as e:
                posting['ai_summary'] = '요약 생성 실패'
                summarized_postings.append(posting)
                print(f"   ❌ Error processing posting {posting.get('posting_id')}: {e}")

        print(f"✅ Generated AI summaries for {len(summarized_postings)} postings")

        # Step 4: Write summarized postings to database
        print("💾 Writing new postings to database...")

        conn = pymysql.connect(
            host=DB_HOST, port=DB_PORT, db=DB_NAME,
            user=DB_USER, password=DB_PASSWORD, charset='utf8mb4'
        )

        try:
            with conn.cursor() as cur:
                # Prepare SQL for inserting postings
                sql = """
                INSERT INTO postings 
                (posting_id, posting_type_id, agency_id, area_province, area_city, 
                 address, application_start, application_end, building_type, 
                 application_url, deposit, rent, summary, rawjson, ai_summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                ai_summary = VALUES(ai_summary),
                summary = VALUES(summary),
                rawjson = VALUES(rawjson)
                """

                inserted_count = 0
                for posting in summarized_postings:
                    try:
                        values = (
                            posting.get('posting_id'),
                            posting.get('posting_type_id', 1),
                            posting.get('agency_id', 'LH'),
                            posting.get('area_province'),
                            posting.get('area_city'),
                            posting.get('address'),
                            posting.get('application_start'),
                            posting.get('application_end'),
                            posting.get('building_type'),
                            posting.get('application_url'),
                            float(posting.get('deposit', 0)) if posting.get('deposit') else None,
                            float(posting.get('rent', 0)) if posting.get('rent') else None,
                            posting.get('summary', ''),
                            posting.get('rawjson'),
                            posting.get('ai_summary', '')
                        )

                        cur.execute(sql, values)
                        inserted_count += 1

                    except Exception as e:
                        print(f"   ❌ Error inserting posting {posting.get('posting_id')}: {e}")

                conn.commit()
                print(f"✅ Successfully inserted/updated {inserted_count} postings in database")

        finally:
            conn.close()

        # Step 5: Generate detail pages for the summarized postings
        print("📄 Generating detail pages for new postings...")

        # Fetch posting types for detail page generation
        posting_types = fetch_all_posting_types()

        detail_pages_generated = 0
        for posting in summarized_postings:
            try:
                # Generate detail page HTML and save to S3
                generate_detail_page_html(
                    posting, 
                    posting_types, 
                    save_local=False,  # Don't save locally in production
                    save_s3=True,
                    s3_bucket='wepl-posting-pages',
                    s3_folder=None
                )
                detail_pages_generated += 1
                print(f"   ✅ Generated detail page for posting {posting.get('posting_id')}")

            except Exception as e:
                print(f"   ❌ Error generating detail page for posting {posting.get('posting_id')}: {e}")

        print(f"✅ Generated {detail_pages_generated} detail pages")

        # Step 6: Update main HTML page with all postings (including new ones)
        print("🔄 Updating main HTML page...")

        success = sync_all_postings_to_html('index.html')
        if success:
            print("✅ Main HTML page updated and uploaded to S3")
        else:
            print("❌ Failed to update main HTML page")

        # Summary
        print("\n🎉 Public API check workflow completed!")
        print(f"   📊 Summary:")
        print(f"   • Total postings from API: {len(lh_postings)}")
        print(f"   • New postings found: {len(new_postings)}")
        print(f"   • Postings with AI summaries: {len(summarized_postings)}")
        print(f"   • Detail pages generated: {detail_pages_generated}")
        print(f"   • Database updated: ✅")
        print(f"   • Main page updated: {'✅' if success else '❌'}")

        return True

    except Exception as e:
        print(f"❌ Error in check_pub_api workflow: {e}")
        return False


# def generate_video():
#     #from db, get newest posting w/o vid url
#     #if posting, send obj to gemini for script
#     #send script to heygen, get vid
#     #save vid to s3
#     #upload vid to youtube api, get yt url
#     #update rds row
#     #generate detail page w/ url
#     #save detail page to s3

#     return


#check_pub_api()

def update_all_detail_pages(save_local=False, save_s3=True, s3_bucket='wepl-posting-pages', s3_folder=None):
    """
    Queries all rows from the database and updates all detail pages.
    Generates fresh detail page HTML for every posting in the database.
    
    Args:
        save_local: Whether to save HTML files locally (default: False)
        save_s3: Whether to save HTML files to S3 (default: True)
        s3_bucket: S3 bucket name for detail pages (default: 'wepl-posting-pages')
        s3_folder: S3 folder prefix (default: None)
    
    Returns:
        dict: Summary of the update process
    """
    print("🚀 Starting update of all detail pages...")
    
    # Initialize counters
    total_postings = 0
    successful_updates = 0
    failed_updates = 0
    failed_posting_ids = []
    
    try:
        # Step 1: Fetch all posting types for detail page generation
        print("📋 Fetching posting types from database...")
        posting_types = fetch_all_posting_types()
        if not posting_types:
            print("❌ Failed to fetch posting types from database")
            return {
                'success': False,
                'error': 'Failed to fetch posting types',
                'total_postings': 0,
                'successful_updates': 0,
                'failed_updates': 0
            }
        print(f"✅ Fetched {len(posting_types)} posting types")
        
        # Step 2: Connect to database and fetch all postings
        print("🔗 Connecting to database...")
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            db=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            charset='utf8mb4'
        )
        
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                # Query all postings ordered by posting_id descending (newest first)
                sql = "SELECT * FROM postings ORDER BY posting_id DESC"
                cur.execute(sql)
                print("📊 Executing query to fetch all postings...")
                
                posting_rows = cur.fetchall()
                total_postings = len(posting_rows)
                print(f"✅ Fetched {total_postings} postings from database")
                
                if total_postings == 0:
                    print("⚠️ No postings found in database")
                    return {
                        'success': True,
                        'message': 'No postings found to update',
                        'total_postings': 0,
                        'successful_updates': 0,
                        'failed_updates': 0
                    }

                # Step 3: Process each posting
                print("🔄 Processing postings and generating detail pages...")
                
                for i, row in enumerate(posting_rows, 1):
                    try:
                        # Convert database row to posting object
                        posting = make_json_serializable(row)
                        posting_id = posting.get('posting_id')
                        
                        print(f"   Processing {i}/{total_postings}: Posting ID {posting_id}")
                        
                        # Generate detail page HTML
                        html_output = generate_detail_page_html(
                            posting, 
                            posting_types, 
                            save_local=save_local,
                            save_s3=save_s3,
                            s3_bucket=s3_bucket,
                            s3_folder=s3_folder
                        )
                        
                        successful_updates += 1
                        print(f"   ✅ Successfully updated detail page for posting {posting_id}")
                        
                        # Add a small delay to avoid overwhelming S3 API
                        if save_s3 and i % 10 == 0:
                            import time
                            time.sleep(0.5)  # 500ms delay every 10 uploads
                        
                    except Exception as e:
                        failed_updates += 1
                        failed_posting_ids.append(posting_id)
                        print(f"   ❌ Failed to update detail page for posting {posting_id}: {e}")
                        continue
                
        finally:
            conn.close()
            print("🔒 Database connection closed")
        
        # Step 4: Summary
        print("\n🎉 Detail page update process completed!")
        print(f"   📊 Summary:")
        print(f"   • Total postings processed: {total_postings}")
        print(f"   • Successful updates: {successful_updates}")
        print(f"   • Failed updates: {failed_updates}")
        print(f"   • Success rate: {(successful_updates/total_postings)*100:.1f}%" if total_postings > 0 else "   • Success rate: 0%")
        
        if failed_posting_ids:
            print(f"   • Failed posting IDs: {failed_posting_ids}")
        
        # Return summary
        return {
            'success': True,
            'total_postings': total_postings,
            'successful_updates': successful_updates,
            'failed_updates': failed_updates,
            'failed_posting_ids': failed_posting_ids,
            'success_rate': (successful_updates/total_postings)*100 if total_postings > 0 else 0
        }
        
    except Exception as e:
        print(f"❌ Error in update_all_detail_pages: {e}")
        return {
            'success': False,
            'error': str(e),
            'total_postings': total_postings,
            'successful_updates': successful_updates,
            'failed_updates': failed_updates,
            'failed_posting_ids': failed_posting_ids
        }


def update_detail_pages_by_agency(agency_id, save_local=False, save_s3=True, s3_bucket='wepl-posting-pages', s3_folder=None):
    """
    Updates detail pages for all postings from a specific agency.
    
    Args:
        agency_id: The agency ID to filter by (e.g., 'LH', 'SH', 'HUG')
        save_local: Whether to save HTML files locally (default: False)
        save_s3: Whether to save HTML files to S3 (default: True)
        s3_bucket: S3 bucket name for detail pages (default: 'wepl-posting-pages')
        s3_folder: S3 folder prefix (default: None)
    
    Returns:
        dict: Summary of the update process
    """
    print(f"🚀 Starting update of detail pages for agency: {agency_id}")
    
    # Initialize counters
    total_postings = 0
    successful_updates = 0
    failed_updates = 0
    failed_posting_ids = []
    
    try:
        # Fetch posting types
        posting_types = fetch_all_posting_types()
        if not posting_types:
            print("❌ Failed to fetch posting types from database")
            return {'success': False, 'error': 'Failed to fetch posting types'}
        
        # Connect to database
        conn = pymysql.connect(
            host=DB_HOST, port=DB_PORT, db=DB_NAME,
            user=DB_USER, password=DB_PASSWORD, charset='utf8mb4'
        )
        
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                # Query postings for specific agency
                sql = "SELECT * FROM postings WHERE agency_id = %s ORDER BY posting_id DESC"
                cur.execute(sql, (agency_id,))
                
                posting_rows = cur.fetchall()
                total_postings = len(posting_rows)
                print(f"✅ Found {total_postings} postings for agency {agency_id}")
                
                if total_postings == 0:
                    return {
                        'success': True,
                        'message': f'No postings found for agency {agency_id}',
                        'total_postings': 0,
                        'successful_updates': 0,
                        'failed_updates': 0
                    }
                
                # Process each posting
                for i, row in enumerate(posting_rows, 1):
                    try:
                        posting = make_json_serializable(row)
                        posting_id = posting.get('posting_id')
                        
                        print(f"   Processing {i}/{total_postings}: Posting ID {posting_id}")
                        
                        generate_detail_page_html(
                            posting, posting_types, 
                            save_local=save_local, save_s3=save_s3,
                            s3_bucket=s3_bucket, s3_folder=s3_folder
                        )
                        
                        successful_updates += 1
                        print(f"   ✅ Updated detail page for posting {posting_id}")
                        
                    except Exception as e:
                        failed_updates += 1
                        failed_posting_ids.append(posting_id)
                        print(f"   ❌ Failed to update posting {posting_id}: {e}")
                
        finally:
            conn.close()
        
        # Summary
        print(f"\n🎉 Agency {agency_id} detail page update completed!")
        print(f"   • Total: {total_postings}, Success: {successful_updates}, Failed: {failed_updates}")
        
        return {
            'success': True,
            'agency_id': agency_id,
            'total_postings': total_postings,
            'successful_updates': successful_updates,
            'failed_updates': failed_updates,
            'failed_posting_ids': failed_posting_ids,
            'success_rate': (successful_updates/total_postings)*100 if total_postings > 0 else 0
        }
        
    except Exception as e:
        print(f"❌ Error updating detail pages for agency {agency_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'agency_id': agency_id,
            'total_postings': total_postings,
            'successful_updates': successful_updates,
            'failed_updates': failed_updates
        }


def remove_obsolete_postings_from_index(html_file_path="index.html"):
    """
    Removes postings from index.html that are no longer present in the database.
    Compares current database postings with HTML file and removes obsolete entries.
    
    Args:
        html_file_path: Path to the HTML file (default: "index.html")
    
    Returns:
        dict: Summary of the removal process
    """
    print("🚀 Starting removal of obsolete postings from index.html...")
    
    try:
        # Step 1: Get current posting IDs from database
        print("📊 Fetching current posting IDs from database...")
        conn = pymysql.connect(
            host=DB_HOST, port=DB_PORT, db=DB_NAME,
            user=DB_USER, password=DB_PASSWORD, charset='utf8mb4'
        )
        
        current_db_posting_ids = set()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT posting_id FROM postings")
                current_db_posting_ids = {str(row[0]) for row in cur.fetchall()}
        finally:
            conn.close()
        
        print(f"✅ Found {len(current_db_posting_ids)} postings in database")
        
        # Step 2: Read current HTML file
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            print(f"❌ Error reading {html_file_path}: {e}")
            return {'success': False, 'error': f'Failed to read HTML file: {e}'}
        
        # Step 3: Extract posting IDs from HTML
        import re
        html_posting_pattern = r'data-notice_id="([^"]+)"'
        html_posting_matches = re.findall(html_posting_pattern, html_content)
        html_posting_ids = set(html_posting_matches)
        
        print(f"✅ Found {len(html_posting_ids)} postings in HTML file")
        
        # Step 4: Identify obsolete postings (in HTML but not in DB)
        obsolete_posting_ids = html_posting_ids - current_db_posting_ids
        
        if not obsolete_posting_ids:
            print("✅ No obsolete postings found. HTML file is up to date.")
            return {
                'success': True,
                'message': 'No obsolete postings found',
                'total_html_postings': len(html_posting_ids),
                'total_db_postings': len(current_db_posting_ids),
                'removed_postings': 0,
                'removed_posting_ids': []
            }
        
        print(f"🗑️ Found {len(obsolete_posting_ids)} obsolete postings to remove: {list(obsolete_posting_ids)}")
        
        # Step 5: Remove obsolete postings from HTML
        updated_html = html_content
        removed_count = 0
        
        for posting_id in obsolete_posting_ids:
            # Pattern to match the entire housing-item div for this posting
            posting_div_pattern = rf'        <div class="housing-item"\s+data-notice_id="{re.escape(posting_id)}"[^>]*>.*?        </div>\n'
            
            # Remove the posting div
            old_length = len(updated_html)
            updated_html = re.sub(posting_div_pattern, '', updated_html, flags=re.DOTALL)
            
            if len(updated_html) < old_length:
                removed_count += 1
                print(f"   ✅ Removed posting {posting_id} from HTML")
            else:
                print(f"   ⚠️ Could not find posting {posting_id} div to remove")
        
        # Step 6: Write updated HTML file
        try:
            with open(html_file_path, 'w', encoding='utf-8') as f:
                f.write(updated_html)
            print(f"✅ Updated {html_file_path} with {removed_count} postings removed")
        except Exception as e:
            print(f"❌ Error writing updated HTML file: {e}")
            return {'success': False, 'error': f'Failed to write HTML file: {e}'}
        
        # Step 7: Upload updated HTML to S3
        try:
            s3 = boto3.client('s3')
            s3.upload_file(
                html_file_path, 
                'wepl-mainpage', 
                os.path.basename(html_file_path), 
                ExtraArgs={'ContentType': 'text/html; charset=utf-8'}
            )
            print(f"✅ Uploaded updated {html_file_path} to S3 bucket wepl-mainpage")
        except Exception as e:
            print(f"⚠️ Warning: Failed to upload to S3: {e}")
        
        # Step 8: Summary
        print(f"\n🎉 Obsolete posting removal completed!")
        print(f"   📊 Summary:")
        print(f"   • Total postings in HTML (before): {len(html_posting_ids)}")
        print(f"   • Total postings in database: {len(current_db_posting_ids)}")
        print(f"   • Obsolete postings identified: {len(obsolete_posting_ids)}")
        print(f"   • Postings successfully removed: {removed_count}")
        print(f"   • Remaining postings in HTML: {len(html_posting_ids) - removed_count}")
        
        return {
            'success': True,
            'total_html_postings': len(html_posting_ids),
            'total_db_postings': len(current_db_posting_ids),
            'obsolete_postings_identified': len(obsolete_posting_ids),
            'removed_postings': removed_count,
            'removed_posting_ids': list(obsolete_posting_ids),
            'remaining_postings': len(html_posting_ids) - removed_count
        }
        
    except Exception as e:
        print(f"❌ Error in remove_obsolete_postings_from_index: {e}")
        return {
            'success': False,
            'error': str(e),
            'removed_postings': 0,
            'removed_posting_ids': []
        }

def sync_index_with_database(html_file_path="index.html"):
    """
    Comprehensive sync function that:
    1. Downloads index.html from S3 if running in Lambda and file doesn't exist locally
    2. Removes obsolete postings from index.html (not in database)
    3. Updates index.html with all current database postings
    4. Uploads the updated file to S3
    
    This ensures the HTML file exactly matches the database state.
    
    Args:
        html_file_path: Path to the HTML file (default: "index.html")
    
    Returns:
        dict: Summary of the sync process
    """
    print("🚀 Starting comprehensive sync of index.html with database...")
    
    try:
        # Step 0: In Lambda environment, download index.html from S3 if it doesn't exist locally
        if is_lambda_environment() and not os.path.exists(html_file_path):
            print("📥 Lambda environment detected - downloading index.html from S3...")
            try:
                s3 = boto3.client('s3')
                s3.download_file('wepl-mainpage', 'index.html', html_file_path)
                print(f"✅ Downloaded index.html from S3 to {html_file_path}")
            except Exception as e:
                print(f"⚠️  Could not download index.html from S3: {e}")
                print("🔧 Creating minimal index.html template...")
                # Create a minimal HTML template
                minimal_html = '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>한눈에 공공임대</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <div id="housing-data" class="hidden">
    </div>

    <script src="script.js"></script>
</body>
</html>'''
                with open(html_file_path, 'w', encoding='utf-8') as f:
                    f.write(minimal_html)
                print("✅ Created minimal index.html template")
        
        # Step 1: Remove obsolete postings first
        print("🗑️ Step 1: Removing obsolete postings...")
        removal_result = remove_obsolete_postings_from_index(html_file_path)
        
        if not removal_result['success']:
            print("❌ Failed to remove obsolete postings")
            return removal_result
        
        print(f"✅ Removed {removal_result['removed_postings']} obsolete postings")
        
        # Step 2: Update with all current database postings
        print("🔄 Step 2: Updating with current database postings...")
        sync_result = sync_all_postings_to_html(html_file_path)
        
        if not sync_result:
            print("❌ Failed to sync current postings")
            return {
                'success': False,
                'error': 'Failed to sync current postings',
                'removal_result': removal_result
            }
        
        # Step 3: Summary
        print("\n🎉 Comprehensive database sync completed!")
        print(f"   📊 Summary:")
        print(f"   • Obsolete postings removed: {removal_result['removed_postings']}")
        print(f"   • Database sync: ✅")
        print(f"   • S3 upload: ✅")
        
        return {
            'success': True,
            'removal_result': removal_result,
            'sync_completed': True,
            'message': 'Index.html successfully synced with database'
        }
        
    except Exception as e:
        print(f"❌ Error in sync_index_with_database: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def complete_lh_workflow(save_local=False, save_s3=True):
    """
    Complete workflow function that:
    1. Fetches postings from LH API
    2. Queries database to filter for new postings only
    3. Generates AI summaries for each new posting
    4. Saves new postings with summaries to database
    5. Generates detail pages for new postings
    6. Updates index.html with all current database postings
    7. Uploads updated index.html to S3
    
    This is the main orchestration function for the entire LH posting pipeline.
    
    Args:
        save_local: Whether to save files locally (default: False)
        save_s3: Whether to save files to S3 (default: True)
    
    Returns:
        dict: Comprehensive summary of the entire workflow
    """
    print("🚀 Starting complete LH workflow...")
    workflow_start_time = datetime.datetime.now()
    
    # Initialize counters and results
    workflow_results = {
        'success': False,
        'start_time': workflow_start_time.isoformat(),
        'api_postings_fetched': 0,
        'new_postings_found': 0,
        'ai_summaries_generated': 0,
        'postings_saved_to_db': 0,
        'detail_pages_generated': 0,
        'index_updated': False,
        'errors': [],
        'execution_time_seconds': 0
    }
    
    try:
        # Step 1: Fetch postings from LH API
        print("📡 Step 1: Fetching postings from LH API...")
        try:
            lh_data = asyncio.run(get_lh_api())
            if not lh_data:
                error_msg = "No data received from LH API"
                print(f"❌ {error_msg}")
                workflow_results['errors'].append(error_msg)
                return workflow_results
            
            # Extract and format LH fields into posting objects
            lh_postings = extract_lh_fields({'response': {'body': {'item': lh_data}}})
            workflow_results['api_postings_fetched'] = len(lh_postings)
            print(f"✅ Extracted {len(lh_postings)} postings from LH API")
            
        except Exception as e:
            error_msg = f"Error fetching from LH API: {str(e)}"
            print(f"❌ {error_msg}")
            workflow_results['errors'].append(error_msg)
            return workflow_results
        
        # Step 2: Filter for new postings (not already in database)
        print("🔍 Step 2: Filtering for new postings...")
        try:
            new_postings = filter_new_postings(lh_postings)
            workflow_results['new_postings_found'] = len(new_postings)
            
            if not new_postings:
                print("✅ No new postings found. Database is up to date.")
                workflow_results['success'] = True
                workflow_results['execution_time_seconds'] = (datetime.datetime.now() - workflow_start_time).total_seconds()
                return workflow_results
            
            print(f"🆕 Found {len(new_postings)} new postings to process")
            
        except Exception as e:
            error_msg = f"Error filtering new postings: {str(e)}"
            print(f"❌ {error_msg}")
            workflow_results['errors'].append(error_msg)
            return workflow_results
        
        # Step 3: Generate AI summaries for each new posting
        print("🤖 Step 3: Generating AI summaries for new postings...")
        summarized_postings = []
        
        for i, posting in enumerate(new_postings, 1):
            print(f"   Processing posting {i}/{len(new_postings)}: {posting.get('posting_id')}")
            try:
                # Convert LH format to standard posting format
                standardized_posting = {
                    'posting_id': posting.get('posting_id'),
                    'posting_type_id': 1,  # Default to LH type
                    'agency_id': 'LH',
                    'area_province': posting.get('prefecture'),
                    'area_city': posting.get('city'),
                    'address': posting.get('detailed_address'),
                    'application_start': posting.get('application_start_date'),
                    'application_end': posting.get('application_end_date'),
                    'building_type': posting.get('building_type'),
                    'application_url': posting.get('application_url'),
                    'deposit': posting.get('deposit'),
                    'rent': posting.get('rent'),
                    'summary': posting.get('posting_summary', ''),
                    'rawjson': json.dumps(posting, ensure_ascii=False),
                    's3_object_address': None,
                    'youtube_url': None
                }
                
                # Generate AI summary
                posting_with_summary = get_ai_summary_for_posting(standardized_posting)
                summarized_postings.append(posting_with_summary)
                workflow_results['ai_summaries_generated'] += 1
                print(f"   ✅ AI summary generated: {posting_with_summary.get('summary', '')[:50]}...")
                
            except Exception as e:
                error_msg = f"Error generating AI summary for posting {posting.get('posting_id')}: {str(e)}"
                print(f"   ❌ {error_msg}")
                workflow_results['errors'].append(error_msg)
                # Add posting without AI summary
                standardized_posting['summary'] = '요약 생성 실패'
                summarized_postings.append(standardized_posting)
        
        print(f"✅ Generated AI summaries for {workflow_results['ai_summaries_generated']} postings")
        
        # Step 4: Save summarized postings to database
        print("💾 Step 4: Saving new postings to database...")
        try:
            conn = pymysql.connect(
                host=DB_HOST, port=DB_PORT, db=DB_NAME,
                user=DB_USER, password=DB_PASSWORD, charset='utf8mb4'
            )
            
            try:
                with conn.cursor() as cur:
                    # Prepare SQL for inserting postings
                    sql = """
                    INSERT INTO postings 
                    (posting_id, posting_type_id, agency_id, area_province, area_city, 
                     address, application_start, application_end, building_type, 
                     application_url, deposit, rent, summary, rawjson)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    summary = VALUES(summary),
                    rawjson = VALUES(rawjson)
                    """
                    
                    for posting in summarized_postings:
                        try:
                            cur.execute(sql, (
                                posting.get('posting_id'),
                                posting.get('posting_type_id', 1),
                                posting.get('agency_id', 'LH'),
                                posting.get('area_province'),
                                posting.get('area_city'),
                                posting.get('address'),
                                posting.get('application_start'),
                                posting.get('application_end'),
                                posting.get('building_type'),
                                posting.get('application_url'),
                                posting.get('deposit'),
                                posting.get('rent'),
                                posting.get('summary'),
                                posting.get('rawjson')
                            ))
                            workflow_results['postings_saved_to_db'] += 1
                            
                        except Exception as e:
                            error_msg = f"Error saving posting {posting.get('posting_id')} to database: {str(e)}"
                            print(f"   ❌ {error_msg}")
                            workflow_results['errors'].append(error_msg)
                    
                    conn.commit()
                    print(f"✅ Successfully saved {workflow_results['postings_saved_to_db']} postings to database")
                    
            finally:
                conn.close()
                
        except Exception as e:
            error_msg = f"Error connecting to database: {str(e)}"
            print(f"❌ {error_msg}")
            workflow_results['errors'].append(error_msg)
            return workflow_results
        
        # Step 5: Generate detail pages for new postings
        print("📄 Step 5: Generating detail pages for new postings...")
        try:
            # Fetch posting types for detail page generation
            posting_types = fetch_all_posting_types()
            if not posting_types:
                error_msg = "Failed to fetch posting types for detail page generation"
                print(f"❌ {error_msg}")
                workflow_results['errors'].append(error_msg)
            else:
                for posting in summarized_postings:
                    try:
                        generate_detail_page_html(
                            posting,
                            posting_types,
                            save_local=save_local,
                            save_s3=save_s3,
                            s3_bucket='wepl-posting-pages',
                            s3_folder=None
                        )
                        workflow_results['detail_pages_generated'] += 1
                        print(f"   ✅ Generated detail page for posting {posting.get('posting_id')}")
                        
                    except Exception as e:
                        error_msg = f"Error generating detail page for posting {posting.get('posting_id')}: {str(e)}"
                        print(f"   ❌ {error_msg}")
                        workflow_results['errors'].append(error_msg)
                
                print(f"✅ Generated {workflow_results['detail_pages_generated']} detail pages")
                
        except Exception as e:
            error_msg = f"Error in detail page generation step: {str(e)}"
            print(f"❌ {error_msg}")
            workflow_results['errors'].append(error_msg)
        
        # Step 6: Update index.html with all current database postings
        print("🔄 Step 6: Updating index.html with current database state...")
        try:
            sync_result = sync_index_with_database('index.html')
            if sync_result and sync_result.get('success'):
                workflow_results['index_updated'] = True
                print("✅ Index.html updated and uploaded to S3")
            else:
                error_msg = f"Failed to update index.html: {sync_result.get('error', 'Unknown error')}"
                print(f"❌ {error_msg}")
                workflow_results['errors'].append(error_msg)
                
        except Exception as e:
            error_msg = f"Error updating index.html: {str(e)}"
            print(f"❌ {error_msg}")
            workflow_results['errors'].append(error_msg)
        
        # Step 7: Final summary
        workflow_end_time = datetime.datetime.now()
        execution_time = (workflow_end_time - workflow_start_time).total_seconds()
        workflow_results['execution_time_seconds'] = execution_time
        workflow_results['end_time'] = workflow_end_time.isoformat()
        
        # Determine overall success
        workflow_results['success'] = (
            workflow_results['new_postings_found'] > 0 and
            workflow_results['postings_saved_to_db'] > 0 and
            workflow_results['index_updated']
        ) or workflow_results['new_postings_found'] == 0  # Success if no new postings found
        
        print("\n🎉 Complete LH workflow finished!")
        print(f"   📊 Final Summary:")
        print(f"   • Execution time: {execution_time:.2f} seconds")
        print(f"   • API postings fetched: {workflow_results['api_postings_fetched']}")
        print(f"   • New postings found: {workflow_results['new_postings_found']}")
        print(f"   • AI summaries generated: {workflow_results['ai_summaries_generated']}")
        print(f"   • Postings saved to database: {workflow_results['postings_saved_to_db']}")
        print(f"   • Detail pages generated: {workflow_results['detail_pages_generated']}")
        print(f"   • Index updated: {'✅' if workflow_results['index_updated'] else '❌'}")
        print(f"   • Overall success: {'✅' if workflow_results['success'] else '❌'}")
        
        if workflow_results['errors']:
            print(f"   • Errors encountered: {len(workflow_results['errors'])}")
            for error in workflow_results['errors']:
                print(f"     - {error}")
        
        return workflow_results
        
    except Exception as e:
        # Catch-all for any unexpected errors
        workflow_end_time = datetime.datetime.now()
        execution_time = (workflow_end_time - workflow_start_time).total_seconds()
        
        error_msg = f"Unexpected error in complete workflow: {str(e)}"
        print(f"❌ {error_msg}")
        
        workflow_results['errors'].append(error_msg)
        workflow_results['execution_time_seconds'] = execution_time
        workflow_results['end_time'] = workflow_end_time.isoformat()
        workflow_results['success'] = False
        
        return workflow_results

def update_recent_detail_pages(days=30, save_local=False, save_s3=True, s3_bucket='wepl-posting-pages', s3_folder=None):
    """
    Updates detail pages for postings created within the last N days.
    
    Args:
        days: Number of recent days to include (default: 30)
        save_local: Whether to save HTML files locally (default: False)
        save_s3: Whether to save HTML files to S3 (default: True)
        s3_bucket: S3 bucket name for detail pages (default: 'wepl-posting-pages')
        s3_folder: S3 folder prefix (default: None)
    
    Returns:
        dict: Summary of the update process
    """
    print(f"🚀 Starting update of detail pages for postings from last {days} days...")
    
    try:
        # Calculate date threshold
        cutoff_date = datetime.date.today() - datetime.timedelta(days=days)
        print(f"📅 Updating postings with application_end >= {cutoff_date}")
        
        # Fetch posting types
        posting_types = fetch_all_posting_types()
        if not posting_types:
            return {'success': False, 'error': 'Failed to fetch posting types'}
        
        # Connect to database
        conn = pymysql.connect(
            host=DB_HOST, port=DB_PORT, db=DB_NAME,
            user=DB_USER, password=DB_PASSWORD, charset='utf8mb4'
        )
        
        total_postings = 0
        successful_updates = 0
        failed_updates = 0
        
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                # Query recent postings
                sql = """
                SELECT * FROM postings 
                WHERE application_end >= %s 
                ORDER BY posting_id DESC
                """
                cur.execute(sql, (cutoff_date,))
                
                posting_rows = cur.fetchall()
                total_postings = len(posting_rows)
                print(f"✅ Found {total_postings} recent postings")
                
                # Process each posting
                for i, row in enumerate(posting_rows, 1):
                    try:
                        posting = make_json_serializable(row)
                        posting_id = posting.get('posting_id')
                        
                        print(f"   Processing {i}/{total_postings}: Posting ID {posting_id}")
                        
                        generate_detail_page_html(
                            posting, posting_types,
                            save_local=save_local, save_s3=save_s3,
                            s3_bucket=s3_bucket, s3_folder=s3_folder
                        )
                        
                        successful_updates += 1
                        
                    except Exception as e:
                        failed_updates += 1
                        print(f"   ❌ Failed to update posting {posting_id}: {e}")
                
        finally:
            conn.close()
        
        print(f"\n🎉 Recent detail pages update completed!")
        print(f"   • Total: {total_postings}, Success: {successful_updates}, Failed: {failed_updates}")
        
        return {
            'success': True,
            'days': days,
            'cutoff_date': cutoff_date.isoformat(),
            'total_postings': total_postings,
            'successful_updates': successful_updates,
            'failed_updates': failed_updates,
            'success_rate': (successful_updates/total_postings)*100 if total_postings > 0 else 0
        }
        
    except Exception as e:
        print(f"❌ Error updating recent detail pages: {e}")
        return {'success': False, 'error': str(e)}



# Main workflow functions for different use cases
# complete_lh_workflow()  # Complete LH API workflow
# get_lh_api()  # Just fetch from API
# filter_new_postings()  # Filter postings
# get_ai_summary_for_posting()  # Generate AI summaries
# save_posting_to_db()  # Save to database
# generate_detail_page_html()  # Generate detail pages
# sync_index_with_database()  # Sync index with database

# Example usage:
# result = complete_lh_workflow()
# print(f"Workflow completed with result: {result}")

# Only run when executed directly, not when imported by Lambda
# complete_lh_workflow()

# sync_index_with_database()

# Execute sync function when run directly
if __name__ == "__main__":
    # Sync index.html with database
    result = sync_index_with_database()
    print(f"Sync result: {result}")
    
    # Optionally, also update recent detail pages locally
    print("\nUpdating recent detail pages locally...")
    detail_result = update_recent_detail_pages(days=30, save_local=True, save_s3=True)
    print(f"Detail pages result: {detail_result}")