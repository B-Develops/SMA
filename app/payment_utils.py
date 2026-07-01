from datetime import datetime
import secrets


def generate_payment_reference():
    return f"SMOTA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4).upper()}"
