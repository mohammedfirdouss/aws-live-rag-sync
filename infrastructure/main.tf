provider "aws" {
  region = var.aws_region
}

module "vpc" {
  source       = "./modules/vpc"
  project_name = var.project_name
}

module "opensearch" {
  source       = "./modules/opensearch"
  project_name = var.project_name
  vpc_id       = module.vpc.vpc_id
  subnet_ids   = module.vpc.private_subnet_ids
}

module "iam" {
  source                    = "./modules/iam"
  project_name              = var.project_name
  opensearch_collection_arn = module.opensearch.collection_arn
}

module "webhook_handler" {
  source        = "./modules/lambda"
  project_name  = var.project_name
  role_arn      = module.iam.lambda_exec_role_arn
  function_name = "webhook_handler"
  handler       = "webhook_handler.handler"
  source_dir    = "${path.module}/../src/ingestion"
  environment_variables = {
    STEP_FUNCTION_ARN = module.step_functions.state_machine_arn
    GITHUB_SECRET     = "TODO_SECRET" # will handle this later
  }
}

module "processor" {
  source        = "./modules/lambda"
  project_name  = var.project_name
  role_arn      = module.iam.lambda_exec_role_arn
  function_name = "processor"
  handler       = "processor.handler"
  source_dir    = "${path.module}/../src/ingestion"
  environment_variables = {
    OPENSEARCH_ENDPOINT = module.opensearch.collection_endpoint
    GITHUB_PAT          = var.github_pat
  }
}

module "index_manager" {
  source        = "./modules/lambda"
  project_name  = var.project_name
  role_arn      = module.iam.lambda_exec_role_arn
  function_name = "index_manager"
  handler       = "index_manager.handler"
  source_dir    = "${path.module}/../src/ingestion"
  environment_variables = {
    OPENSEARCH_ENDPOINT = module.opensearch.collection_endpoint
  }
}

module "rag_agent" {
  source        = "./modules/lambda"
  project_name  = var.project_name
  role_arn      = module.iam.lambda_exec_role_arn
  function_name = "rag_agent"
  handler       = "rag_agent.handler"
  source_dir    = "${path.module}/../src/query"
  environment_variables = {
    OPENSEARCH_ENDPOINT = module.opensearch.collection_endpoint
  }
}

module "step_functions" {
  source                   = "./modules/step_functions"
  project_name             = var.project_name
  role_arn                 = module.iam.lambda_exec_role_arn
  processor_lambda_arn     = module.processor.function_arn
  index_manager_lambda_arn = module.index_manager.function_arn
}

module "apigateway" {
  source                       = "./modules/apigateway"
  project_name                 = var.project_name
  webhook_lambda_invoke_arn    = module.webhook_handler.invoke_arn
  webhook_lambda_function_name = module.webhook_handler.function_name
  query_lambda_invoke_arn      = module.rag_agent.invoke_arn
  query_lambda_function_name   = module.rag_agent.function_name
}

output "api_url" {
  value = module.apigateway.api_url
}
