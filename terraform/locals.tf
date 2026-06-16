# Set tags with name prefix from environment
locals {
  full_function_name = var.name_prefix != "" ? "${var.name_prefix}-${var.function_name}" : var.function_name
  effective_tags = merge(
    var.tags,
    var.name_prefix != "" ? { Owner = var.name_prefix } : {}
  )

  full_api_name        = var.name_prefix != "" ? "${var.name_prefix}-${var.api_name}" : var.api_name
  full_table_name      = var.name_prefix != "" ? "${var.name_prefix}-${var.dynamodb_table_name}" : var.dynamodb_table_name
  full_repository_name = "${local.full_function_name}-repo"

  project_root = abspath("${path.module}/..")
  source_files = concat(
    tolist(fileset(local.project_root, "src/**")),
    ["requirements.txt"]
  )
  image_source_hash = sha256(join("", concat(
    [for file in local.source_files : filesha256("${local.project_root}/${file}")],
    [filesha256("${path.module}/Dockerfile.lambda")]
  )))
}
