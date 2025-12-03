import json
import os
import hmac
import hashlib
import boto3

sfn_client = boto3.client('stepfunctions')

def validate_signature(headers, body, secret):
    signature = headers.get('X-Hub-Signature-256')
    if not signature:
        return False
    
    hash_object = hmac.new(secret.encode('utf-8'), msg=body.encode('utf-8'), digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

def handler(event, context):
    print("Received event:", json.dumps(event))
    

    headers = event.get('headers', {})
    body = event.get('body', '')
    
    # Fetch secret from Secrets Manager
    # github_secret = get_secret(os.environ['GITHUB_SECRET_ARN'])
    github_secret = "TODO_SECRET" # Placeholder
    
    if not validate_signature(headers, body, github_secret):
        return {
            "statusCode": 401,
            "body": json.dumps({"message": "Invalid signature"})
        }
    
    payload = json.loads(body)
    

    commits = payload.get('commits', [])
    files_to_process = []
    
    for commit in commits:
        for file in commit.get('added', []):
            files_to_process.append({"path": file, "status": "added", "commit_sha": commit['id']})
        
   
        for file in commit.get('modified', []):
            files_to_process.append({"path": file, "status": "modified", "commit_sha": commit['id']})
            
        for file in commit.get('removed', []):
            files_to_process.append({"path": file, "status": "removed", "commit_sha": commit['id']})
            
    if not files_to_process:
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "No files to process"})
        }
        

    sfn_arn = os.environ['STEP_FUNCTION_ARN']
    execution_input = {
        "files": files_to_process,
        "repository": payload.get('repository', {}).get('full_name')
    }
    
    response = sfn_client.start_execution(
        stateMachineArn=sfn_arn,
        input=json.dumps(execution_input)
    )
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Ingestion started", "executionArn": response['executionArn']})
    }
