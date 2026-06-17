variable "aws_project" {
  description = "The AWS project name."
  type        = string
  default     = "coding-workshop"
}

variable "aws_bucket" {
  description = "The AWS S3 bucket name for terraform state storage."
  type        = string
  default     = "coding-workshop-us-east-1-abcd1234"
}

variable "aws_app_code" {
  description = "The AWS application unique code."
  type        = string
  default     = "abcd1234"
}

variable "aws_vpc_id" {
  description = "The AWS VPC identifier."
  type        = string
  default     = null
}

variable "aws_postgres_enabled" {
  description = "Enable or disable PostgreSQL (AWS Aurora). Default: true (set to 'false' to disable it)."
  type        = bool
  default     = true
}

variable "aws_postgres_host" {
  description = "PostgreSQL host for LocalStack. Default: 'host.docker.internal' (set to '172.17.0.1' on Linux)."
  type        = string
  default     = null
}

variable "aws_mongo_enabled" {
  description = "Enable or disable MongoDB (AWS DocumentDB). Default: false (set to 'true' to enable it)."
  type        = bool
  default     = false
}

variable "aws_mongo_host" {
  description = "MongoDB host for LocalStack. Default: 'host.docker.internal' (set to '172.17.0.1' on Linux)."
  type        = string
  default     = null
}

variable "jwt_secret" {
  description = "Secret used to sign JWT access/refresh tokens. Set a strong value for AWS (e.g. TF_VAR_jwt_secret)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "admin_email" {
  description = "Bootstrap admin email, seeded on first run if no admin exists."
  type        = string
  default     = "admin@coding-workshop.local"
}

variable "admin_password" {
  description = "Bootstrap admin password, seeded on first run. Set a strong value for AWS (e.g. TF_VAR_admin_password)."
  type        = string
  default     = ""
  sensitive   = true
}
