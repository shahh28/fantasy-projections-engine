import json
from datetime import datetime

def lambda_handler(event, context):
    """Lambda handler for health check"""
    try:
        # Basic health check without external dependencies
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "function_name": context.function_name,
            "function_version": context.function_version,
            "aws_region": context.invoked_function_arn.split(':')[3],
            "memory_limit": context.memory_limit_in_mb,
            "remaining_time": context.get_remaining_time_in_millis(),
            "message": "Fantasy Sports API is running!"
        }
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(health_status)
        }
        
    except Exception as e:
        print(f"Error in health check: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        } 