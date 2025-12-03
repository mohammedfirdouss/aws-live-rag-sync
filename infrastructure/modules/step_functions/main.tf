variable "project_name" {
  type = string
}

variable "role_arn" {
  type = string
}

variable "processor_lambda_arn" {
  type = string
}

variable "index_manager_lambda_arn" {
  type = string
}

resource "aws_sfn_state_machine" "ingestion_workflow" {
  name     = "${var.project_name}-ingestion"
  role_arn = var.role_arn

  definition = jsonencode({
    Comment = "Ingestion Workflow for Live RAG"
    StartAt = "ProcessFiles"
    States = {
      ProcessFiles = {
        Type = "Map"
        ItemsPath = "$.files"
        Parameters = {
          "path.$": "$$.Map.Item.Value.path",
          "status.$": "$$.Map.Item.Value.status",
          "commit_sha.$": "$$.Map.Item.Value.commit_sha",
          "repository.$": "$.repository"
        }
        Iterator = {
          StartAt = "DetermineAction"
          States = {
            DetermineAction = {
              Type = "Choice"
              Choices = [
                {
                  Variable = "$.status"
                  StringEquals = "removed"
                  Next = "DeleteIndex"
                }
              ]
              Default = "ProcessContent"
            }
            ProcessContent = {
              Type = "Task"
              Resource = var.processor_lambda_arn
              End = true
            }
            DeleteIndex = {
              Type = "Task"
              Resource = var.index_manager_lambda_arn
              End = true
            }
          }
        }
        End = true
      }
    }
  })
}

output "state_machine_arn" {
  value = aws_sfn_state_machine.ingestion_workflow.arn
}
