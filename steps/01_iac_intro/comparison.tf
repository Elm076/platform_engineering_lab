# Reference comparison only (not executed in this demo).
# Compare this Terraform HCL against `steps/01_iac_intro/__main__.py`.

variable "project_id" {
  type = string
}

variable "env" {
  type    = string
  default = "prod"
}

resource "google_storage_bucket" "app_storage" {
  name                        = "${var.project_id}-demo-api-${var.env}"
  location                    = "EUROPE-WEST4"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true
}

resource "google_storage_bucket_object" "app_storage_seed" {
  name         = "welcome.json"
  bucket       = google_storage_bucket.app_storage.name
  content_type = "application/json"
  content = jsonencode({
    message = "Hello from Google Cloud Storage managed by IaC!"
    env     = var.env
    event   = "DevFest Jaén 2026"
  })
}

output "bucket_name" {
  value = google_storage_bucket.app_storage.name
}
