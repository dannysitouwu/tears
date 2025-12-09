variable "hcloud_token" {
  description = "Hetzner Cloud API Token"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "SSH public key for server access"
  type        = string
}

variable "server_type" {
  description = "Hetzner server type"
  type        = string
  default     = "cx22" # 2 vCPU, 4GB RAM, 40GB SSD
}

variable "location" {
  description = "Hetzner datacenter location"
  type        = string
  default     = "nbg1" # Nuremberg
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "github_repo" {
  description = "GitHub repository URL"
  type        = string
  default     = "https://github.com/dannysitouwu/tears.git"
}

variable "postgres_volume_size" {
  description = "PostgreSQL volume size in GB"
  type        = number
  default     = 10
}

variable "monitoring_allowed_ips" {
  description = "IP addresses allowed to access monitoring dashboards"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Change this to your IP for security
}

variable "enable_load_balancer" {
  description = "Enable load balancer for high availability"
  type        = bool
  default     = false
}
