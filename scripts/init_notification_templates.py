"""
Script to initialize default notification templates in the database.

This script loads all default notification templates and creates them
in the database if they don't already exist.
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_async_session
from backend.app.db.repositories.notifications import NotificationRepository
from backend.app.services.notification_templates import get_all_default_templates


async def initialize_default_templates():
    """Initialize default notification templates in the database."""

    print("🔄 Initializing default notification templates...")

    async for session in get_async_session():
        try:
            repo = NotificationRepository(session)
            templates = get_all_default_templates()

            created_count = 0
            updated_count = 0
            skipped_count = 0

            for template_config in templates:
                try:
                    # Check if template already exists
                    existing_template = await repo.get_template_by_name(template_config["name"])

                    if existing_template:
                        # Update existing template
                        updated_template = await repo.update_template(
                            template_id=existing_template.id,
                            name=template_config["name"],
                            event_type=template_config["event_type"],
                            channel=template_config["channel"],
                            subject=template_config["subject"],
                            body_template=template_config["body_template"],
                            variables=template_config["variables"],
                            priority=template_config["priority"],
                            locale=template_config["locale"]
                        )

                        if updated_template:
                            print(f"✅ Updated template: {template_config['name']}")
                            updated_count += 1
                        else:
                            print(f"⚠️  Failed to update template: {template_config['name']}")
                    else:
                        # Create new template
                        new_template = await repo.create_template(
                            name=template_config["name"],
                            event_type=template_config["event_type"],
                            channel=template_config["channel"],
                            subject=template_config["subject"],
                            body_template=template_config["body_template"],
                            variables=template_config["variables"],
                            priority=template_config["priority"],
                            locale=template_config["locale"]
                        )

                        if new_template:
                            print(f"✅ Created template: {template_config['name']}")
                            created_count += 1
                        else:
                            print(f"⚠️  Failed to create template: {template_config['name']}")

                except Exception as e:
                    print(f"❌ Error processing template {template_config['name']}: {str(e)}")
                    skipped_count += 1
                    continue

            print(f"\n📊 Template Initialization Summary:")
            print(f"   • Created: {created_count} templates")
            print(f"   • Updated: {updated_count} templates")
            print(f"   • Skipped: {skipped_count} templates")
            print(f"   • Total: {len(templates)} templates processed")

            if created_count > 0 or updated_count > 0:
                print("\n🎉 Default notification templates initialized successfully!")
            else:
                print("\nℹ️  All templates were already up to date.")

        except Exception as e:
            print(f"❌ Failed to initialize templates: {str(e)}")
            raise

        finally:
            await session.close()


async def main():
    """Main function to run the template initialization."""
    try:
        await initialize_default_templates()
    except Exception as e:
        print(f"❌ Script failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
