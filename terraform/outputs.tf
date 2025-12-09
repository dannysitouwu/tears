output "backend_server_ip" {
  description = "Public IP address of the backend server"
  value       = hcloud_server.backend.ipv4_address
}

output "backend_server_ipv6" {
  description = "IPv6 address of the backend server"
  value       = hcloud_server.backend.ipv6_address
}

output "backend_server_name" {
  description = "Name of the backend server"
  value       = hcloud_server.backend.name
}

output "postgres_volume_id" {
  description = "ID of the PostgreSQL data volume"
  value       = hcloud_volume.postgres_data.id
}

output "load_balancer_ip" {
  description = "Public IP of the load balancer (if enabled)"
  value       = var.enable_load_balancer ? hcloud_load_balancer.tears[0].ipv4 : null
}

output "ssh_connection" {
  description = "SSH connection command"
  value       = "ssh root@${hcloud_server.backend.ipv4_address}"
}

output "api_url" {
  description = "API base URL"
  value       = var.enable_load_balancer ? "http://${hcloud_load_balancer.tears[0].ipv4}" : "http://${hcloud_server.backend.ipv4_address}:8000"
}

output "grafana_url" {
  description = "Grafana dashboard URL"
  value       = "http://${hcloud_server.backend.ipv4_address}:3000"
}

output "prometheus_url" {
  description = "Prometheus URL"
  value       = "http://${hcloud_server.backend.ipv4_address}:9090"
}
