import re

# Read the file
with open('tests/unit/test_idempotency.py', 'r') as f:
    content = f.read()

# Fix payments missing payment_method by searching for Payment( patterns that don't have payment_method
# Pattern: Payment(...) that contains provider_name but not payment_method
payment_pattern = r'(Payment\(\s*\n[^)]*?provider_name="[^"]*"[^)]*?)(\s*\))'

def fix_missing_payment_method(match):
    payment_content = match.group(1)
    closing = match.group(2)

    # Check if payment_method is already present
    if 'payment_method=' in payment_content:
        return match.group(0)  # Return unchanged

    # Add payment_method before the closing parenthesis
    return payment_content + ',\n            payment_method="credit_card"' + closing

content = re.sub(payment_pattern, fix_missing_payment_method, content, flags=re.MULTILINE | re.DOTALL)

# Write back
with open('tests/unit/test_idempotency.py', 'w') as f:
    f.write(content)

print("Fixed all missing payment_method fields")
