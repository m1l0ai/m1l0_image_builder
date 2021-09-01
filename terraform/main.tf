terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

provider "aws" {
  shared_credentials_file = var.aws_credentials
  region                  = var.aws_region
  profile                 = var.aws_profile
}

locals {
  account_id = data.aws_caller_identity.current.account_id
}


# Setup IAM roles etc...
resource "aws_iam_policy" "rexraypolicy" {
  name        = "${var.grpc_service_name}-ebsRexRayPolicy"
  description = "Policy for RexRay plugin for EBS volumes"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "ec2:AttachVolume",
          "ec2:CreateVolume",
          "ec2:CreateSnapshot",
          "ec2:CreateTags",
          "ec2:DeleteVolume",
          "ec2:DeleteSnapshot",
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeInstances",
          "ec2:DescribeVolumes",
          "ec2:DescribeVolumeAttribute",
          "ec2:DescribeVolumeStatus",
          "ec2:DescribeSnapshots",
          "ec2:CopySnapshot",
          "ec2:DescribeSnapshotAttribute",
          "ec2:DetachVolume",
          "ec2:ModifySnapshotAttribute",
          "ec2:ModifyVolumeAttribute",
          "ec2:DescribeTags"
        ],
        Resource = "*"
    }]
  })
}

# Create ECS Instance Role
resource "aws_iam_role" "ecs_instance_role" {
  name = "${var.grpc_service_name}-ecsInstanceRole"

  description = "IAM Role for ECS Container Instance"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "ec2.amazonaws.com"
        },
        Effect = "Allow",
        "Sid" : ""
      }
    ]
  })
}

# Attach RexRayPolicy to instance role
resource "aws_iam_role_policy_attachment" "ecs-instance-role-rexray-policy-attachment" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = aws_iam_policy.rexraypolicy.arn
}

# Attach EC2 Service Role
resource "aws_iam_role_policy_attachment" "ecs_instance_ec2_instance_role" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

# Create EC2 Instance Profile needed for running EC2 on ECS
resource "aws_iam_instance_profile" "ecs_instance_profile" {
  name = "${var.grpc_service_name}-ecsInstanceProfile"
  role = aws_iam_role.ecs_instance_role.name
}


# Task execution role
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.grpc_service_name}-ecsTaskExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          AWS     = data.aws_caller_identity.current.arn,
          Service = "ecs-tasks.amazonaws.com"
        },
        Effect = "Allow",
        Sid    = ""
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "task_role_attach_s3" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "task_role_attach_cloudwatch_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSOpsWorksCloudWatchLogs"
}

# Allows ECS containers to read secrets from KMS..
resource "aws_iam_policy" "kms_policy" {
  name        = "${var.grpc_service_name}-ecsKMSPolicy"
  description = "Policy for handling KMS secrets in ECS"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "ssm:GetParameters",
          "secretsmanager:GetSecretValue",
          "kms:Decrypt"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "task_role_attach_kms" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.kms_policy.arn
}