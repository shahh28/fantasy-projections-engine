import boto3
import json
import pandas as pd
import numpy as np
from datetime import datetime
import os

def get_s3_client():
    """Get S3 client"""
    return boto3.client('s3')

def upload_to_s3(data, bucket, key, content_type='application/json'):
    """Upload data to S3"""
    s3_client = get_s3_client()
    
    if isinstance(data, pd.DataFrame):
        data = data.to_json(orient='records')
    elif isinstance(data, dict):
        data = json.dumps(data)
    
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type
    )

def download_from_s3(bucket, key):
    """Download data from S3"""
    s3_client = get_s3_client()
    
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        
        # Try to parse as JSON first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # If not JSON, try to parse as CSV
            return pd.read_json(content)
    except Exception as e:
        print(f"Error downloading from S3: {e}")
        return None

def list_s3_objects(bucket, prefix=''):
    """List objects in S3 bucket with prefix"""
    s3_client = get_s3_client()
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        return [obj['Key'] for obj in response.get('Contents', [])]
    except Exception as e:
        print(f"Error listing S3 objects: {e}")
        return []

def create_response(status_code, body, headers=None):
    """Create API Gateway response"""
    if headers is None:
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        }
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body) if isinstance(body, (dict, list)) else body
    }

def get_environment_variables():
    """Get environment variables"""
    return {
        'S3_BUCKET': os.environ.get('S3_BUCKET'),
        'MODEL_BUCKET': os.environ.get('MODEL_BUCKET')
    }

def log_event(event, context):
    """Log Lambda event and context"""
    print(f"Event: {json.dumps(event)}")
    print(f"Context: {context.function_name} - {context.aws_request_id}")

def validate_request_body(body, required_fields):
    """Validate request body has required fields"""
    if not body:
        return False, "Request body is required"
    
    missing_fields = [field for field in required_fields if field not in body]
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, None 