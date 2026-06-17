resource "oci_core_vcn" "narrative_vcn" {
  cidr_block     = "10.0.0.0/16"
  compartment_id = var.compartment_id
  display_name   = "narrative-vcn"
  dns_label      = "narrativevcn"
}

resource "oci_core_internet_gateway" "narrative_ig" {
  compartment_id = var.compartment_id
  display_name   = "narrative-internet-gateway"
  vcn_id         = oci_core_vcn.narrative_vcn.id
}

resource "oci_core_default_route_table" "narrative_rt" {
  manage_default_resource_id = oci_core_vcn.narrative_vcn.default_route_table_id
  display_name               = "narrative-route-table"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.narrative_ig.id
  }
}

resource "oci_core_subnet" "narrative_subnet" {
  cidr_block        = "10.0.1.0/24"
  display_name      = "narrative-public-subnet"
  compartment_id    = var.compartment_id
  vcn_id            = oci_core_vcn.narrative_vcn.id
  route_table_id    = oci_core_vcn.narrative_vcn.default_route_table_id
  security_list_ids = [oci_core_vcn.narrative_vcn.default_security_list_id, oci_core_security_list.narrative_security_list.id]
  dns_label         = "public"
}
