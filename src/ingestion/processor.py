import json
import os
import base64
import boto3
import urllib3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

# Dependencies (would need a Layer in production)
# import requests
# from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

bedrock = boto3.client('bedrock-runtime')
http = urllib3.PoolManager()

def get_github_content(repo, path, pat):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "LiveRAG"
    }
    response = http.request('GET', url, headers=headers)
    
    if response.status != 200:
        print(f"Failed to fetch file: {response.status} {response.data}")
        return None
        
    data = json.loads(response.data.decode('utf-8'))
    content = base64.b64decode(data['content']).decode('utf-8')
    return content

def chunk_text(text, chunk_size=1000, overlap=100):
    # Simple chunking for now
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

def get_embedding(text):
    body = json.dumps({
        "inputText": text
    })
    
    response = bedrock.invoke_model(
        body=body,
        modelId="amazon.titan-embed-text-v2:0",
        accept="application/json",
        contentType="application/json"
    )
    
    response_body = json.loads(response.get('body').read())
    return response_body.get('embedding')

def index_document(index_name, doc_id, vector, text, metadata, endpoint):
    region = os.environ['AWS_REGION']
    credentials = boto3.Session().get_credentials()
    
    url = f"{endpoint}/{index_name}/_doc/{doc_id}"
    body = json.dumps({
        "vector_field": vector,
        "text": text,
        "metadata": metadata
    })
    
    request = AWSRequest(method='PUT', url=url, data=body, headers={'Content-Type': 'application/json'})
    SigV4Auth(credentials, 'aoss', region).add_auth(request)
    
    response = http.request(
        'PUT', 
        url, 
        body=body, 
        headers=dict(request.headers)
    )
    
    return response.status

def handler(event, context):
    print("Received event:", json.dumps(event))
    
    # Event comes from Step Functions Map state: {"path": "...", "status": "...", "commit_sha": "..."}
    # But wait, the Map state iterates over the list.
    # We also need the 'repository' from the input.
    # The Step Function definition I wrote passes the item as input.
    # I need to adjust Step Function to pass repository info or include it in the item.
    # For now, let's assume the event contains 'path', 'repository', 'commit_sha'.
    
    path = event.get('path')
    repo = event.get('repository')
    sha = event.get('commit_sha')
    pat = os.environ.get('GITHUB_PAT')
    endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
    
    if not pat:
        return {"statusCode": 500, "body": "Missing GITHUB_PAT"}
        
    content = get_github_content(repo, path, pat)
    if not content:
        return {"statusCode": 404, "body": "File not found"}
        
    chunks = chunk_text(content)
    
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        doc_id = f"{sha}-{path}-{i}".replace('/', '-')
        
        metadata = {
            "path": path,
            "repository": repo,
            "commit_sha": sha,
            "chunk_index": i
        }
        
        status = index_document("rag-index", doc_id, embedding, chunk, metadata, endpoint)
        print(f"Indexed chunk {i}: {status}")
        
    return {"statusCode": 200, "body": f"Processed {len(chunks)} chunks"}
