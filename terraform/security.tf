resource "oci_core_security_list" "narrative_security_list" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.narrative_vcn.id
  display_name   = "narrative-security-list"

  # SSH (restrict via var.ssh_source_cidr; set to your IP/32 or CI CIDR; use 0.0.0.0/0 only if required)
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = var.ssh_source_cidr
    description = "Allow SSH access from ssh_source_cidr (set to your IP/32 or CI/CD CIDR for security)"
    tcp_options {
      min = 22
      max = 22
    }
  }

  # HTTP
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    description = "Allow HTTP access"
    tcp_options {
      min = 80
      max = 80
    }
  }

  # HTTPS
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    description = "Allow HTTPS access"
    tcp_options {
      min = 443
      max = 443
    }
  }

  # Voice Agent (LiveKit/WebRTC)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    description = "Allow LiveKit TCP"
    tcp_options {
      min = 8081
      max = 8081
    }
  }

  # Narrative AI API Endpoints
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    description = "Allow Narrative AI API access"
    tcp_options {
      min = 8000
      max = 8003
    }
  }

  # Outbound rule (allow all)
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
}
