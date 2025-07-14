#!/usr/bin/env python3
"""
Simple script to update the health check Lambda function
"""

import os
import zipfile
import tempfile
import subprocess
import json

def create_deployment_package():
    """Create a deployment package for the health check function"""
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the health check function
        health_check_code = '''
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
            "aws_region": context.invoked_function_arn.split(":")[3],
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
'''
        
        # Write the function code
        with open(os.path.join(temp_dir, 'health_check.py'), 'w') as f:
            f.write(health_check_code)
        
        # Create zip file
        zip_path = os.path.join(temp_dir, 'health_check.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(os.path.join(temp_dir, 'health_check.py'), 'health_check.py')
        
        # Read the zip file
        with open(zip_path, 'rb') as f:
            return f.read()

def update_lambda_function():
    """Update the health check Lambda function"""
    
    try:
        # Get the function name
        result = subprocess.run([
            'aws', 'cloudformation', 'describe-stacks',
            '--stack-name', 'fantasy-sports-predictor',
            '--query', 'Stacks[0].Outputs[?OutputKey==`HealthCheckFunction`].OutputValue',
            '--output', 'text'
        ], capture_output=True, text=True, check=True)
        
        function_name = result.stdout.strip()
        if not function_name:
            # Try to find the function name from the stack resources
            result = subprocess.run([
                'aws', 'cloudformation', 'list-stack-resources',
                '--stack-name', 'fantasy-sports-predictor'
            ], capture_output=True, text=True, check=True)
            
            resources = json.loads(result.stdout)
            for resource in resources['StackResourceSummaries']:
                if 'HealthCheckFunction' in resource['LogicalResourceId']:
                    function_name = resource['PhysicalResourceId']
                    break
        
        if not function_name:
            print("Could not find HealthCheckFunction name")
            return False
        
        print(f"Updating function: {function_name}")
        
        # Create deployment package
        deployment_package = create_deployment_package()
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            temp_file.write(deployment_package)
            temp_file_path = temp_file.name
        
        try:
            # Update the function
            subprocess.run([
                'aws', 'lambda', 'update-function-code',
                '--function-name', function_name,
                '--zip-file', f'fileb://{temp_file_path}'
            ], check=True)
            
            print("✅ Health check function updated successfully!")
            return True
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error updating function: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Updating health check Lambda function...")
    success = update_lambda_function()
    
    if success:
        print("\n🎉 Health check function updated! Testing...")
        # Test the function
        import requests
        try:
            response = requests.get("https://bmvkco3289.execute-api.us-east-1.amazonaws.com/Prod/health")
            if response.status_code == 200:
                print("✅ Health check is working!")
                print(f"Response: {response.json()}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"❌ Error testing health check: {e}")
    else:
        print("❌ Failed to update health check function") 