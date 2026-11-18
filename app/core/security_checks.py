"""Startup par unsafe configuration ki warnings."""


def security_warnings(s) -> list[str]:
    warnings = []
    if not s.api_key:
        warnings.append("API_KEY khali hai: core endpoints bina key ke khule hain")
    if s.auth_secret and len(s.auth_secret) < 32:
        warnings.append("AUTH_SECRET 32 characters se chhota hai: lamba random secret use karein")
    if not s.dashboard_password:
        warnings.append("DASHBOARD_PASSWORD khali hai: dashboard bina password ke khula hai")
    if s.debug:
        warnings.append("DEBUG on hai: production me DEBUG=false rakhein")
    return warnings