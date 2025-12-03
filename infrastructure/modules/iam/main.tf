variable "project_name" {
  type = string
}

variable "opensearch_collection_arn" {
  type = string
}

# Lambda Execution Role (Basic)
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for Bedrock Access
resource "aws_iam_policy" "bedrock_access" {
  name        = "${var.project_name}-bedrock-access"
  description = "Allow access to Bedrock models"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "bedrock:InvokeModel"
        ]
        Effect   = "Allow"
        Resource = "*" # Restrict to specific models in production
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_bedrock" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.bedrock_access.arn
}

# Policy for OpenSearch Access (Data Plane)
resource "aws_iam_policy" "opensearch_access" {
  name        = "${var.project_name}-opensearch-access"
  description = "Allow access to OpenSearch Serverless data"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "aoss:APIAccessAll"
        ]
        Effect   = "Allow"
        Resource = var.opensearch_collection_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_opensearch" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.opensearch_access.arn
}

output "lambda_exec_role_arn" {
  value = aws_iam_role.lambda_exec.arn
}
