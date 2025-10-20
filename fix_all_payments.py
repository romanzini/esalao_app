import re

# Read the file
with open('tests/unit/test_idempotency.py', 'r') as f:
    content = f.read()

# Find all Payment constructions and fix them one by one
lines = content.split('\n')
result_lines = []
i = 0

while i < len(lines):
    line = lines[i]

    # Check if this line starts a Payment construction
    if 'Payment(' in line and '=' in line:
        # Collect all lines until the closing parenthesis
        payment_lines = [line]
        j = i + 1
        open_parens = line.count('(')
        close_parens = line.count(')')

        while j < len(lines) and open_parens > close_parens:
            payment_lines.append(lines[j])
            open_parens += lines[j].count('(')
            close_parens += lines[j].count(')')
            j += 1

        # Check if payment_method is missing but provider_name is present
        payment_text = '\n'.join(payment_lines)
        if 'payment_method=' not in payment_text and 'provider_name=' in payment_text:
            # Find the line with currency and add payment_method after it
            for k, pline in enumerate(payment_lines):
                if 'currency=' in pline:
                    # Insert payment_method line after currency
                    payment_lines.insert(k + 1, '            payment_method="credit_card",')
                    break

        # Add all payment lines to result
        result_lines.extend(payment_lines)
        i = j
    else:
        result_lines.append(line)
        i += 1

# Write back
content = '\n'.join(result_lines)
with open('tests/unit/test_idempotency.py', 'w') as f:
    f.write(content)

print("Fixed all Payment constructions")
