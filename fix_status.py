import re

# Read the file
with open('tests/unit/test_idempotency.py', 'r') as f:
    content = f.read()

# Replace PaymentStatus.PENDING with string
content = re.sub(r'status=PaymentStatus\.PENDING,', 'status="pending",', content)

# Write back
with open('tests/unit/test_idempotency.py', 'w') as f:
    f.write(content)

print("Replaced all PaymentStatus.PENDING with string values")
