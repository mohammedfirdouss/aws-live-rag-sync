# AWS-Live-RAG-Sync

A serverless event-driven **Live RAG (Retrieval-Augmented Generation)** system that syncs knowledge from GitHub and enables real-time semantic search and question-answering using AWS services.

## Overview

This project implements a production-ready RAG system with two main pipelines:

- **Ingestion Pipeline**: Automatically syncs GitHub repository changes to a vector database
- **Query Pipeline**: Provides semantic search and AI-powered question answering

Built with AWS Lambda, Step Functions, OpenSearch Serverless, and Amazon Bedrock.

## Key Features

✅ **Event-Driven Architecture** - GitHub webhooks trigger automatic ingestion  
✅ **Vector Search** - OpenSearch Serverless for semantic similarity  
✅ **AI-Powered Responses** - Amazon Bedrock (Claude, Titan embeddings)  
✅ **Serverless** - No infrastructure management required  
✅ **Secure** - HMAC-based webhook validation, IAM role-based access  
✅ **Scalable** - Step Functions orchestration handles complex workflows  

## Real-World Scenario

**Imagine you have a large documentation repository with hundreds of markdown files, guides, and API references.**

### Without Live RAG:
- Users search through GitHub manually
- Documentation is scattered across files
- Answers require reading multiple documents
- Updates aren't immediately searchable

### With Live RAG:
1. **Developer writes documentation** and pushes to GitHub
   ```
   $ git push origin main
   → GitHub webhook fires automatically
   ```

2. **System automatically ingests** the new content
   ```
   ✓ File fetched from GitHub
   ✓ Content split into chunks
   ✓ Embeddings generated (Bedrock Titan)
   ✓ Vectors indexed (OpenSearch)
   ```

3. **User asks a natural language question**
   ```
   Q: "How do I set up authentication?"
   ```

4. **System finds relevant documentation** and generates answer
   ```
   A: "To set up authentication, you need to configure OAuth2 credentials...
       [Retrieved from: setup-guide.md, authentication.md]"
   ```

This enables intelligent, up-to-date question answering on your knowledge base without manual indexing.

## Architecture

The system implements an event-driven architecture with clear separation of concerns:

### Ingestion Flow
1. GitHub repository receives a push
2. Webhook triggers API Gateway endpoint
3. Webhook handler validates HMAC signature
4. Step Functions orchestrates the ingestion:
   - **Process Lambda**: Fetches files from GitHub, chunks content, generates embeddings
   - **Index Manager**: Upserts/deletes documents in OpenSearch Serverless
5. Vector index stays synchronized with source repository

### Query Flow
1. User submits a natural language question via API
2. Query Lambda processes the request:
   - Generates embedding for the query using Bedrock Titan
   - Performs k-NN vector search in OpenSearch
   - Retrieves relevant document chunks
   - Generates contextual answer using Claude via Bedrock
3. Returns structured JSON response with answer and sources


## Technologies

| Layer | Technology |
|-------|------------|
| **Compute** | AWS Lambda, Step Functions |
| **API** | API Gateway (REST) |
| **Vector DB** | OpenSearch Serverless |
| **AI/ML** | Amazon Bedrock (Claude 3.5 Sonnet, Titan Embeddings) |
| **Infrastructure** | Terraform |
| **Agent Framework** | Strands SDK |

## Getting Started

### Prerequisites

- AWS Account with credentials configured
- Terraform >= 1.0
- GitHub Personal Access Token (PAT) with `repo` scope
- AWS CLI v2

### Installation & Deployment

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd aws-live-rag-sync
   ```

2. **Initialize Terraform**
   ```bash
   cd infrastructure
   terraform init
   ```

3. **Deploy infrastructure**
   ```bash
   terraform apply -var="github_pat=YOUR_GITHUB_PAT"
   ```

4. **Configure GitHub Webhook**
   - Go to your GitHub repo → Settings → Webhooks → Add webhook
   - **Payload URL**: `{api_gateway_url}/webhook`
   - **Content type**: `application/json`
   - **Secret**: Configure in Lambda environment variables
   - **Events**: Push events

5. **Verify deployment**
   - See [walkthrough.md](./walkthrough.md) for verification steps

## Usage

### Trigger Ingestion (Push to GitHub)
```bash
# Add/modify a file in the repository
echo "Your documentation or code..." > new_file.md
git add new_file.md
git commit -m "Add new content"
git push
```

The file will automatically be processed and indexed.

### Query the RAG System
```bash
# Submit a question
curl -X POST {api_gateway_url}/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How does the ingestion pipeline work?"
  }'
```

Response format:
```json
{
  "answer": "The ingestion pipeline uses GitHub webhooks to...",
  "sources": [
    {
      "file": "README.md",
      "chunk": 0,
      "score": 0.92
    }
  ],
  "timestamp": "2025-12-03T10:30:00Z"
}
```

## API Endpoints

### POST /webhook
Receives GitHub push events and triggers ingestion.

**Headers:**
- `X-Hub-Signature-256`: HMAC signature for validation

**Body:** GitHub webhook payload

**Response:**
```json
{
  "statusCode": 200,
  "body": {
    "message": "Ingestion started",
    "executionArn": "arn:aws:states:..."
  }
}
```

### POST /query
Submits a question and returns RAG-generated answer.

**Body:**
```json
{
  "question": "Your question here"
}
```

**Response:**
```json
{
  "answer": "Generated answer",
  "sources": [...],
  "timestamp": "ISO-8601 timestamp"
}
```

## Configuration

### Environment Variables

Set in Lambda functions:

- `GITHUB_PAT`: GitHub Personal Access Token
- `GITHUB_REPO`: Repository in format `owner/repo`
- `OPENSEARCH_ENDPOINT`: OpenSearch Serverless endpoint
- `OPENSEARCH_INDEX`: Index name for vector storage
- `BEDROCK_REGION`: AWS region for Bedrock models

### Models Used

- **Embeddings**: `amazon.titan-embed-text-v2:0`
- **Generation**: `claude-3-5-sonnet-20241022`

## Security

- ✅ GitHub webhook signature validation (HMAC-SHA256)
- ✅ IAM role-based access control
- ✅ OpenSearch Serverless with VPC endpoint
- ✅ Least privilege Lambda execution roles
- ✅ Secrets Manager for sensitive data

## Monitoring & Logs

CloudWatch Logs available at:
- `/aws/lambda/webhook_handler`
- `/aws/lambda/processor`
- `/aws/lambda/index_manager`
- `/aws/lambda/query_rag`

## Development

### Local Testing

The codebase includes:
- `webhook_handler.py`: Validates and routes GitHub events
- `processor.py`: Handles text chunking and embedding generation
- `index_manager.py`: Manages OpenSearch operations
- `rag_agent.py`: RAG agent with tool integration (Strands SDK)

### Adding New Features

1. Modify relevant Lambda function in `src/`
2. Update Terraform module if infrastructure changes needed
3. Test locally, then deploy with `terraform apply`


## Contributing

Contributions welcome! Please follow the existing code structure and update documentation accordingly.

## References

- [AWS Lambda](https://aws.amazon.com/lambda/)
- [OpenSearch Serverless](https://aws.amazon.com/opensearch-service/serverless/)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [Strands SDK](https://github.com/strands-ai/strands-sdk)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)