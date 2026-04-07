resource "aws_route53_record" "n8n_ipv4" {
  count   = var.route53_zone_id != "" && var.n8n_domain_name != "" ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.n8n_domain_name
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "n8n_ipv6" {
  count   = var.route53_zone_id != "" && var.n8n_domain_name != "" ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.n8n_domain_name
  type    = "AAAA"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = false
  }
}
