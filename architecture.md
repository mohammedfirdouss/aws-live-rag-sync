# Live RAG System Architecture

This document describes the event-driven architecture of the Live RAG System.

## High-Level Architecture

The system is composed of two main pipelines: **Ingestion** (keeping knowledge in sync) and **Query** (retrieving answers).

```mermaid
graph LR
    subgraph External["External Sources"]
        User["User / Developer"]
        GitHub["GitHub Repo (Push Event)"]
    end

    subgraph AWS["AWS Cloud"]
        style AWS fill:#f9f9f9,stroke:#232f3e,stroke-width:2px
        
        subgraph Ingestion["Ingestion Pipeline"]
            style Ingestion fill:#e6f3ff,stroke:#0073bb,stroke-dasharray: 5 5
            
            APIGW_Web["API Gateway (Webhook)"]
            Lambda_Web["Lambda: webhook_handler"]
            SFN["Step Functions: Ingestion"]
            Lambda_Proc["Lambda: process_file"]
            Lambda_Idx["Lambda: index_manager"]
        end

        subgraph Storage["Storage & AI"]
            style Storage fill:#fff4e6,stroke:#d05c15,stroke-dasharray: 5 5
            
            OSS["OpenSearch Serverless (Vector)"]
            Bedrock["Amazon Bedrock (Titan/Claude)"]
        end

        subgraph Query["Query Pipeline"]
            style Query fill:#e6fffa,stroke:#00a169,stroke-dasharray: 5 5
            
            APIGW_Query["API Gateway (Query)"]
            Lambda_Query["Lambda: query_rag"]
        end
    end

    %% Ingestion Flow
    GitHub -->|POST /webhook| APIGW_Web
    APIGW_Web -->|Proxy| Lambda_Web
    Lambda_Web -->|Start Execution| SFN
    SFN -->|1. Fetch & Chunk| Lambda_Proc
    Lambda_Proc -->|Embed Text| Bedrock
    Lambda_Proc -->|Chunks + Vectors| SFN
    SFN -->|2. Upsert/Delete| Lambda_Idx
    Lambda_Idx -->|Index Documents| OSS

    %% Query Flow
    User -->|POST /query| APIGW_Query
    APIGW_Query -->|Proxy| Lambda_Query
    Lambda_Query -->|1. Embed Query| Bedrock
    Lambda_Query -->|2. Vector Search| OSS
    OSS -->|Relevant Chunks| Lambda_Query
    Lambda_Query -->|3. Generate Answer| Bedrock
    Bedrock -->|Answer| Lambda_Query
    Lambda_Query -->|JSON Response| User

    %% Styling
    classDef aws fill:#FF9900,stroke:#232f3e,stroke-width:1px,color:white
    classDef ext fill:#ddd,stroke:#333,stroke-width:1px
    
    class APIGW_Web,APIGW_Query,Lambda_Web,Lambda_Proc,Lambda_Idx,Lambda_Query,SFN,OSS,Bedrock aws
    class User,GitHub ext
```

---

## Detailed Pipeline Architectures

### Ingestion Pipeline Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GitHub as GitHub
    participant APIGW as API Gateway
    participant Lambda_WH as Webhook Handler
    participant SFN as Step Functions
    participant Lambda_Proc as Processor Lambda
    participant Bedrock as Amazon Bedrock
    participant Lambda_Idx as Index Manager
    participant OSS as OpenSearch

    Dev->>GitHub: git push
    GitHub->>APIGW: POST /webhook + signature
    APIGW->>Lambda_WH: Invoke with event
    Lambda_WH->>Lambda_WH: Validate HMAC
    alt Signature Valid
        Lambda_WH->>SFN: Start Execution
        SFN->>Lambda_Proc: Fetch files & chunk
        Lambda_Proc->>GitHub: GET file content
        Lambda_Proc->>Lambda_Proc: Split into chunks
        Lambda_Proc->>Bedrock: Generate embeddings
        Bedrock->>Lambda_Proc: Return vectors
        Lambda_Proc->>SFN: Return chunks + vectors
        SFN->>Lambda_Idx: Upsert to index
        Lambda_Idx->>OSS: Index documents
        OSS->>Lambda_Idx: Confirm indexed
        Lambda_Idx->>SFN: Complete
    else Invalid Signature
        Lambda_WH->>APIGW: Return 401 Unauthorized
    end
```

### Query Pipeline Flow

```mermaid
sequenceDiagram
    participant User
    participant APIGW as API Gateway
    participant Lambda_Query as Query Lambda
    participant Bedrock as Amazon Bedrock
    participant OSS as OpenSearch

    User->>APIGW: POST /query with question
    APIGW->>Lambda_Query: Invoke with question
    Lambda_Query->>Bedrock: Generate query embedding
    Bedrock->>Lambda_Query: Return embedding vector
    Lambda_Query->>OSS: k-NN vector search
    OSS->>Lambda_Query: Return top-k chunks
    Lambda_Query->>Bedrock: Generate answer with context
    Bedrock->>Lambda_Query: Return generated answer
    Lambda_Query->>APIGW: JSON response
    APIGW->>User: Answer + sources
```

### Data Flow Diagram

```mermaid
graph TB
    subgraph Input["Input Sources"]
        GitPush["GitHub Push Event"]
        UserQuery["User Query"]
    end

    subgraph Processing["Processing Layer"]
        HMAC["HMAC Validation"]
        Embed["Embedding Generation"]
        Chunk["Text Chunking"]
        RAGPrompt["RAG Prompt Construction"]
    end

    subgraph Storage["Storage Layer"]
        VectorDB["Vector Database<br/>OpenSearch Serverless"]
        ChunkStore["Chunk Storage"]
    end

    subgraph AI["AI/ML Layer"]
        TitanEmbed["Titan Embeddings"]
        ClaudeGen["Claude Generation"]
    end

    subgraph Output["Output"]
        IngestionConfirm["Indexed Confirmation"]
        AnswerResponse["Answer + Sources"]
    end

    GitPush -->|Webhook Event| HMAC
    HMAC -->|Valid| Chunk
    Chunk -->|Text Segments| Embed
    Embed -->|Uses| TitanEmbed
    TitanEmbed -->|Vectors| VectorDB
    Chunk -->|Stored| ChunkStore
    
    UserQuery -->|Question| Embed
    Embed -->|Uses| TitanEmbed
    TitanEmbed -->|Query Vector| VectorDB
    VectorDB -->|Relevant Chunks| RAGPrompt
    ChunkStore -->|Chunk Details| RAGPrompt
    RAGPrompt -->|Context| ClaudeGen
    ClaudeGen -->|Generated Answer| AnswerResponse
    
    VectorDB -->|Confirmed| IngestionConfirm
```

---

## Component Details

### 1. Ingestion Pipeline

```mermaid
graph TD
    A["GitHub Push Event"] -->|Webhook| B["API Gateway<br/>/webhook"]
    B --> C["Lambda: webhook_handler"]
    C -->|HMAC Validation| D{Valid?}
    D -->|No| E["Return 401"]
    D -->|Yes| F["Extract File List"]
    F --> G["Start Step Functions<br/>Execution"]
    G --> H["Step Functions<br/>Orchestration"]
    H --> I["Lambda: process_file"]
    I -->|Fetch from GitHub| J["Get File Content"]
    J --> K["Chunk Text<br/>size=1000, overlap=100"]
    K --> L["Generate Embeddings<br/>Titan Model"]
    L --> M["Lambda: index_manager"]
    M -->|Upsert/Delete| N["OpenSearch Serverless<br/>Vector Index"]
    N --> O["Indexing Complete"]
```

### 2. Query Pipeline

```mermaid
graph TD
    A["User Question"] -->|HTTP POST| B["API Gateway<br/>/query"]
    B --> C["Lambda: query_rag"]
    C --> D["Generate Query<br/>Embedding"]
    D -->|Titan Model| E["Query Vector"]
    E --> F["k-NN Vector Search<br/>k=3"]
    F --> G["OpenSearch Serverless"]
    G --> H["Return Top-K<br/>Relevant Chunks"]
    H --> I["Construct RAG<br/>Prompt"]
    I --> J["Claude 3.5 Sonnet<br/>Generation"]
    J --> K["Generated Answer"]
    K --> L["Format Response<br/>+ Sources"]
    L --> M["JSON Response<br/>to User"]
```

### 3. Infrastructure Components

```mermaid
graph LR
    subgraph VPC["VPC"]
        SG["Security Group<br/>Port 443"]
        VPCEndpoint["VPC Endpoint"]
    end

    subgraph OpenSearch["OpenSearch Serverless"]
        Collection["Vector Collection<br/>Type: VECTORSEARCH"]
        EncPolicy["Encryption Policy<br/>AWS-Owned Key"]
        NetPolicy["Network Policy<br/>VPC Access"]
    end

    subgraph Lambda["Lambda Functions"]
        WH["webhook_handler<br/>Runtime: Python 3.11"]
        Proc["processor<br/>Runtime: Python 3.11"]
        Idx["index_manager<br/>Runtime: Python 3.11"]
        Query["query_rag<br/>Runtime: Python 3.11"]
    end

    subgraph Bedrock["Amazon Bedrock"]
        Titan["Titan Embeddings<br/>amazon.titan-embed-text-v2"]
        Claude["Claude 3.5 Sonnet<br/>claude-3-5-sonnet-20241022"]
    end

    subgraph Gateway["API Gateway"]
        WebhookEndpoint["POST /webhook"]
        QueryEndpoint["POST /query"]
    end

    VPC --> VPCEndpoint
    VPCEndpoint --> Collection
    Collection --> EncPolicy
    Collection --> NetPolicy
    
    WebhookEndpoint --> WH
    WH --> Proc
    Proc --> Idx
    Idx --> Collection
    
    QueryEndpoint --> Query
    Query --> Collection
    
    Proc --> Titan
    Query --> Titan
    Query --> Claude
```

---

## Component Details

### 1. Ingestion Pipeline
*   **Trigger**: GitHub Webhook on `git push`.
*   **Webhook Handler**: Validates HMAC signature and triggers Step Functions.
*   **Step Functions**: Orchestrates the ingestion process.
*   **Process Lambda**: Fetches file content from GitHub, chunks it, and generates embeddings using **Amazon Bedrock**.
*   **Index Manager**: Updates the **OpenSearch Serverless** vector index (Upsert or Delete).

### 2. Query Pipeline
*   **Trigger**: HTTP POST request to `/query`.
*   **Query Lambda**:
    1.  Converts user question to vector embedding via **Bedrock**.
    2.  Performs k-NN search on **OpenSearch Serverless**.
    3.  Constructs a prompt with retrieved context.
    4.  Generates final answer using **Bedrock** (Claude 3.5 Sonnet).

### 3. Storage & AI
*   **OpenSearch Serverless**: Stores document chunks and their vector embeddings.
*   **Amazon Bedrock**: Provides Foundation Models for embedding (Titan) and text generation (Claude).
