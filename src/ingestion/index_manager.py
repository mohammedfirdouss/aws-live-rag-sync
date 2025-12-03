import json
import os
import boto3
import urllib3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

http = urllib3.PoolManager()

def delete_documents(index_name, path, endpoint):
    region = os.environ['AWS_REGION']
    credentials = boto3.Session().get_credentials()
    
    url = f"{endpoint}/{index_name}/_delete_by_query"
    body = json.dumps({
        "query": {
            "term": {
                "metadata.path.keyword": path 
            }
        }
    })
    
    request = AWSRequest(method='POST', url=url, data=body, headers={'Content-Type': 'application/json'})
    SigV4Auth(credentials, 'aoss', region).add_auth(request)
    
    response = http.request(
        'POST', 
        url, 
        body=body, 
        headers=dict(request.headers)
    )
    
    return response.status, response.data

def handler(event, context):
    print("Received event:", json.dumps(event))
    
    path = event.get('path')
    endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
    
    if not path:
        return {"statusCode": 400, "body": "Missing path"}
        
    status, response_data = delete_documents("rag-index", path, endpoint)
    print(f"Delete status: {status}, response: {response_data}")
    
    return {"statusCode": status, "body": "Deletion processed"}
