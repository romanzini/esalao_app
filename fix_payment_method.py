import re

# Read the file
with open('tests/unit/test_idempotency.py', 'r') as f:
    content = f.read()

# Fix payment_method - add it to all Payment() creations that don't have it
content = re.sub(
    r'(Payment\([^)]*?)(\s*status=)',
    r'\1\n            payment_method="credit_card",\2',
    content
)

# Fix remaining PaymentStatus enums using lower() function
def fix_enum(match):
    enum_value = match.group(1)
    return f'"{enum_value.lower()}"'

content = re.sub(r'PaymentStatus\.(PENDING|PROCESSING|SUCCEEDED|FAILED|CANCELED|REFUNDED|PARTIALLY_REFUNDED)', fix_enum, content)
content = re.sub(r'RefundStatus\.(PENDING|PROCESSING|SUCCEEDED|FAILED|CANCELED)', fix_enum, content)

# Write back
with open('tests/unit/test_idempotency.py', 'w') as f:
    f.write(content)

print("Fixed payment_method field and remaining enum values")
