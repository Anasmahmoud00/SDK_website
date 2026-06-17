variable "tenancy_ocid" {
  description = "OCI Tenancy OCID"
  type        = string
}

variable "user_ocid" {
  description = "OCI User OCID"
  type        = string
}

variable "fingerprint" {
  description = "OCI API Key Fingerprint"
  type        = string
}

variable "private_key_path" {
  description = "Path to the OCI API private key file"
  type        = string
  default     = "./keys/oci_api_key.pem"
}

variable "region" {
  description = "OCI Region (e.g., us-ashburn-1, eu-frankfurt-1)"
  type        = string
  default     = "eu-frankfurt-1"
}

variable "compartment_id" {
  description = "OCI Compartment OCID"
  type        = string
}

variable "ssh_public_key_path" {
  description = "Path to your SSH public key"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "instance_shape" {
  description = "Always Free shape: VM.Standard.A1.Flex (ARM, 1-4 OCPU) or VM.Standard.E2.1.Micro (x86, 1 OCPU / 1 GB fixed). Use E2.1.Micro when A1 is 'Out of host capacity'; then set IMAGE_PLATFORM=linux/amd64 in GitHub Secrets."
  type        = string
  default     = "VM.Standard.A1.Flex"
}

variable "instance_ocpus" {
  description = "Number of OCPUs for the ARM instance"
  type        = number
  default     = 4
}

variable "instance_memory_in_gbs" {
  description = "Memory in GBs for the ARM instance"
  type        = number
  default     = 24
}

variable "ssh_source_cidr" {
  description = "CIDR block for allowed SSH access. WARNING: 0.0.0.0/0 allows everyone! Use your-ip/32 for production."
  type        = string
  default     = "CHANGEME/32" # Forces the user to provide a value or intentionally use 0.0.0.0/0
}

variable "availability_domain_index" {
  description = "Availability Domain index (0, 1, or 2). Use when AD-1 returns 'Out of host capacity' for A1.Flex."
  type        = number
  default     = 0
}
