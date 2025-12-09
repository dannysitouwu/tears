terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.44"
    }
  }
  
  backend "s3" {
    # Configure remote state (optional but recommended)
    # bucket = "your-terraform-state-bucket"
    # key    = "tears/terraform.tfstate"
    # region = "us-east-1"
  }
}

provider "hcloud" {
  token = var.hcloud_token
}

# SSH Key for server access
resource "hcloud_ssh_key" "tears" {
  name       = "tears-deployment-key"
  public_key = var.ssh_public_key
}

# Server for backend and database
resource "hcloud_server" "backend" {
  name        = "tears-backend"
  server_type = var.server_type
  image       = "ubuntu-22.04"
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.tears.id]

  labels = {
    environment = var.environment
    app         = "tears"
    role        = "backend"
  }

  user_data = templatefile("${path.module}/cloud-init-backend.yaml", {
    github_repo = var.github_repo
  })
}

# Firewall rules
resource "hcloud_firewall" "backend" {
  name = "tears-backend-firewall"

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "22"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "80"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "443"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "8000"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }

  # Prometheus
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "9090"
    source_ips = var.monitoring_allowed_ips
  }

  # Grafana
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "3000"
    source_ips = var.monitoring_allowed_ips
  }
}

resource "hcloud_firewall_attachment" "backend" {
  firewall_id = hcloud_firewall.backend.id
  server_ids  = [hcloud_server.backend.id]
}

# Volume for PostgreSQL data
resource "hcloud_volume" "postgres_data" {
  name      = "tears-postgres-data"
  size      = var.postgres_volume_size
  location  = var.location
  format    = "ext4"
  
  labels = {
    environment = var.environment
    app         = "tears"
    role        = "database"
  }
}

resource "hcloud_volume_attachment" "postgres_data" {
  volume_id = hcloud_volume.postgres_data.id
  server_id = hcloud_server.backend.id
  automount = true
}

# Load balancer (optional, for high availability)
resource "hcloud_load_balancer" "tears" {
  count = var.enable_load_balancer ? 1 : 0
  
  name               = "tears-lb"
  load_balancer_type = "lb11"
  location           = var.location

  labels = {
    environment = var.environment
    app         = "tears"
  }
}

resource "hcloud_load_balancer_target" "backend" {
  count = var.enable_load_balancer ? 1 : 0
  
  type             = "server"
  load_balancer_id = hcloud_load_balancer.tears[0].id
  server_id        = hcloud_server.backend.id
}

resource "hcloud_load_balancer_service" "http" {
  count = var.enable_load_balancer ? 1 : 0
  
  load_balancer_id = hcloud_load_balancer.tears[0].id
  protocol         = "http"
  listen_port      = 80
  destination_port = 80

  health_check {
    protocol = "http"
    port     = 80
    interval = 15
    timeout  = 10
    retries  = 3
    http {
      path         = "/health"
      status_codes = ["200"]
    }
  }
}

resource "hcloud_load_balancer_service" "https" {
  count = var.enable_load_balancer ? 1 : 0
  
  load_balancer_id = hcloud_load_balancer.tears[0].id
  protocol         = "https"
  listen_port      = 443
  destination_port = 443

  health_check {
    protocol = "http"
    port     = 80
    interval = 15
    timeout  = 10
    retries  = 3
    http {
      path         = "/health"
      status_codes = ["200"]
    }
  }
}
