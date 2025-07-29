import json
import os
import boto3
from apitest03 import (
    generate_detail_page_html,
    generate_html_for_all_postings,
    generate_html_for_specific_postings,
    sync_all_postings_to_html,
    fetch_all_posting_types,
    make_json_serializable,
    get_newest_posting_without_video,
    generate_ai_summaries_for_all_postings
)
import pymysql

def lambda_handler(event, context):
    """
    AWS Lambda handler for generating and uploading housing detail pages.
    
    Event structure:
    {
        "action": "generate_all|generate_specific|sync_index|generate_summaries",
        "posting_ids": [1, 2, 3],  # Only for generate_specific
        "s3_detail_bucket": "wepl-posting-pages",
        "s3_main_bucket": "wepl-mainpage"
    }
    """
    
    try:
        # Parse event data
        action = event.get('action', 'generate_all')
        s3_detail_bucket = event.get('s3_detail_bucket', 'wepl-posting-pages')
        s3_main_bucket = event.get('s3_main_bucket', 'wepl-mainpage')
        posting_ids = event.get('posting_ids', [])
        
        print(f"Lambda execution started - Action: {action}")
        print(f"S3 Detail Bucket: {s3_detail_bucket}")
        print(f"S3 Main Bucket: {s3_main_bucket}")
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        results = {}
        
        if action == 'generate_all':
            # Generate detail pages for all postings and save to S3
            print("Generating HTML for all postings...")
            results = generate_html_for_all_postings(
                save_local=False,  # Don't save locally in Lambda
                save_s3=True,
                s3_bucket=s3_detail_bucket,
                s3_folder=None
            )
            
        elif action == 'generate_specific':
            if not posting_ids:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'posting_ids required for generate_specific action'
                    })
                }
            
            print(f"Generating HTML for specific postings: {posting_ids}")
            results = generate_html_for_specific_postings(
                posting_ids=posting_ids,
                save_local=False,
                save_s3=True,
                s3_bucket=s3_detail_bucket,
                s3_folder=None
            )
            
        elif action == 'sync_index':
            # Update index.html with latest database data and upload to main S3 bucket
            print("Syncing index.html with database...")
            
            # Generate updated index.html locally first
            success = sync_all_postings_to_html('index.html')
            
            if success:
                # Upload index.html to main bucket
                try:
                    s3_client.upload_file(
                        'index.html', 
                        s3_main_bucket, 
                        'index.html',
                        ExtraArgs={'ContentType': 'text/html; charset=utf-8'}
                    )
                    results = {
                        'success': True,
                        'message': f'index.html updated and uploaded to {s3_main_bucket}'
                    }
                    print(f"Successfully uploaded index.html to {s3_main_bucket}")
                except Exception as e:
                    results = {
                        'success': False,
                        'error': f'Failed to upload index.html to S3: {str(e)}'
                    }
            else:
                results = {
                    'success': False,
                    'error': 'Failed to sync index.html with database'
                }
                
        elif action == 'generate_summaries':
            # Generate AI summaries for postings without them
            print("Generating AI summaries for postings...")
            success = generate_ai_summaries_for_all_postings()
            results = {
                'success': success,
                'message': 'AI summary generation completed' if success else 'AI summary generation failed'
            }
            
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Unknown action: {action}'
                })
            }
        
        # Return success response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'action': action,
                'results': results
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"Lambda execution error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'action': event.get('action', 'unknown')
            })
        }

def test_lambda_locally():
    """Test function to run Lambda handler locally"""
    
    # Test event for generating all postings
    test_event = {
        "action": "generate_all",
        "s3_detail_bucket": "wepl-posting-pages",
        "s3_main_bucket": "wepl-mainpage"
    }
    
    result = lambda_handler(test_event, None)
    print("Test result:", json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_lambda_locally()