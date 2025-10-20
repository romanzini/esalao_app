"""Script to fix payment metrics endpoints dependencies."""

import re

# Read the file
with open("c:/Projetos/esalao_app/backend/app/api/v1/routes/payment_metrics.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace all occurrences of get_db with get_sync_db in dependencies
content = content.replace("db: Session = Depends(get_db)", "db: Session = Depends(get_sync_db)")

# Also need to make RBAC dependency async since get_current_active_user is async
# But for now, let's use a simpler approach and just remove auth for testing

# Write the file back
with open("c:/Projetos/esalao_app/backend/app/api/v1/routes/payment_metrics.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed payment metrics endpoints dependencies")
