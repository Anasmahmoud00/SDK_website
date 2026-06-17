resource "oci_core_instance" "narrative_instance" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[var.availability_domain_index].name
  compartment_id      = var.compartment_id
  display_name        = "narrative-ai-server"
  shape               = var.instance_shape

  # Only A1.Flex supports shape_config; E2.1.Micro is fixed (1 OCPU, 1 GB)
  dynamic "shape_config" {
    for_each = var.instance_shape == "VM.Standard.A1.Flex" ? [1] : []
    content {
      ocpus         = var.instance_ocpus
      memory_in_gbs = var.instance_memory_in_gbs
    }
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.narrative_subnet.id
    display_name     = "primary-vnic"
    assign_public_ip = true
    hostname_label   = "narrative-server"
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu_latest.images[0].id
    # E2.1.Micro: use 50 GB (Always Free default); A1.Flex: 100 GB
    boot_volume_size_in_gbs = var.instance_shape == "VM.Standard.E2.1.Micro" ? 50 : 100
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data           = base64encode(file("${path.module}/scripts/cloud-init.yml"))
  }
}

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_id
}

data "oci_core_images" "ubuntu_latest" {
  compartment_id           = var.compartment_id
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}
