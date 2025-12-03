import json
import os
import boto3
import urllib3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials


from strands import Agent, tool
from strands.models import BedrockModel

bedrock = boto3.client('bedrock-runtime')
http = urllib3.PoolManager()

# --- Helper Functions (kept for the tool to use) ---

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

def search_vectors(index_name, vector, endpoint, k=3):
    region = os.environ['AWS_REGION']
    credentials = boto3.Session().get_credentials()
    
    url = f"{endpoint}/{index_name}/_search"
    body = json.dumps({
        "size": k,
        "query": {
            "knn": {
                "vector_field": {
                    "vector": vector,
                    "k": k
                }
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
    
    if response.status != 200:
        print(f"Search failed: {response.status} {response.data}")
        return []
        
    data = json.loads(response.data.decode('utf-8'))
    hits = data.get('hits', {}).get('hits', [])
    return hits


@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the project codebase/knowledge base for relevant information.
    Use this tool when you need to answer questions about the code, architecture, or implementation details.
    
    Args:
        query: The search query string.
    """
    print(f"Tool called with query: {query}")
    endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
    
    if not endpoint:
        return "Error: OPENSEARCH_ENDPOINT not configured."

    query_vector = get_embedding(query)
    
    hits = search_vectors("rag-index", query_vector, endpoint)
    
    context_text = ""
    if not hits:
        return "No relevant code found."
        
    for hit in hits:
        source = hit.get('_source', {})
        path = source.get('metadata', {}).get('path', 'unknown')
        text = source.get('text', '')
        context_text += f"--- File: {path} ---\n{text}\n\n"
        
    return context_text

def handler(event, context):
    print("Received event:", json.dumps(event))
    
    body = json.loads(event.get('body', '{}'))
    user_query = body.get('query')
    
    if not user_query:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Missing query"})
        }
    
   
    model = BedrockModel(
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
        temperature=0.1 
    )
    
    agent = Agent(
        model=model,
        tools=[search_knowledge_base],
        system_prompt="You are a helpful AI coding assistant. Use the search_knowledge_base tool to find relevant code before answering."
    )
    
    try:
        response_text = agent(user_query)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": response_text,
                "query": user_query
            })
        }
    except Exception as e:
        print(f"Agent error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Internal error: {str(e)}"})
        }
