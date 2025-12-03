variable "project_name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

resource "aws_security_group" "opensearch" {
  name        = "${var.project_name}-opensearch-sg"
  description = "Security group for OpenSearch Serverless"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"] # Allow access from within VPC
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_opensearchserverless_collection" "vector" {
  name = "${var.project_name}-vec"
  type = "VECTORSEARCH"
}

resource "aws_opensearchserverless_vpc_endpoint" "endpoint" {
  name               = "${var.project_name}-vpce"
  vpc_id             = var.vpc_id
  subnet_ids         = var.subnet_ids
  security_group_ids = [aws_security_group.opensearch.id]
}

# Encryption Policy
resource "aws_opensearchserverless_security_policy" "encryption" {
  name        = "${var.project_name}-enc"
  type        = "encryption"
  description = "Encryption policy for Live RAG"
  policy = jsonencode({
    Rules = [
      {
        ResourceType = "collection"
        Resource = [
          "collection/${aws_opensearchserverless_collection.vector.name}"
        ]
      }
    ]
    AWSOwnedKey = true
  })
}

# Network Policy
resource "aws_opensearchserverless_security_policy" "network" {
  name        = "${var.project_name}-net"
  type        = "network"
  description = "Network policy for Live RAG"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/${aws_opensearchserverless_collection.vector.name}"
          ]
        },
        {
          ResourceType = "dashboard"
          Resource = [
            "collection/${aws_opensearchserverless_collection.vector.name}"
          ]
        }
      ]
      AllowFromPublic = true # For ease of testing, can restrict later
    }
  ])
}

output "collection_endpoint" {
  value = aws_opensearchserverless_collection.vector.collection_endpoint
}

output "collection_arn" {
  value = aws_opensearchserverless_collection.vector.arn
}
