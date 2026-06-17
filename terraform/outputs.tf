output "instance_public_ip" {
  value       = oci_core_instance.narrative_instance.public_ip
  description = "Public IP of the Narrative AI server"
}

output "ssh_command" {
  value       = "ssh -i YOUR_PRIVATE_KEY ubuntu@${oci_core_instance.narrative_instance.public_ip}"
  description = "Command to SSH into the server"
}
