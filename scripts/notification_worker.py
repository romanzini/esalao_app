"""
Background worker for processing notification queue.

This worker continuously processes pending notifications from the queue,
handling retries, rate limiting, and delivery tracking.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_async_session
from backend.app.services.notifications import NotificationService
from backend.app.core.config import settings


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('notification_worker.log')
    ]
)

logger = logging.getLogger(__name__)


class NotificationWorker:
    """Background worker for processing notification queue."""

    def __init__(self, batch_size: int = 50, sleep_interval: int = 30):
        """
        Initialize the notification worker.

        Args:
            batch_size: Number of notifications to process per batch
            sleep_interval: Seconds to sleep between processing cycles
        """
        self.batch_size = batch_size
        self.sleep_interval = sleep_interval
        self.running = False
        self.stats = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "start_time": None
        }

    async def start(self):
        """Start the notification worker."""
        self.running = True
        self.stats["start_time"] = datetime.now()

        logger.info("🚀 Starting notification worker...")
        logger.info(f"   • Batch size: {self.batch_size}")
        logger.info(f"   • Sleep interval: {self.sleep_interval}s")

        while self.running:
            try:
                # Process a batch of notifications
                await self._process_batch()

                # Sleep before next cycle
                if self.running:  # Check if still running before sleeping
                    await asyncio.sleep(self.sleep_interval)

            except Exception as e:
                logger.error(f"❌ Error in worker cycle: {str(e)}")
                await asyncio.sleep(self.sleep_interval)  # Sleep on error to prevent tight loop

    async def stop(self):
        """Stop the notification worker gracefully."""
        logger.info("🛑 Stopping notification worker...")
        self.running = False

        # Log final statistics
        runtime = datetime.now() - self.stats["start_time"]
        logger.info("📊 Worker Statistics:")
        logger.info(f"   • Runtime: {runtime}")
        logger.info(f"   • Total processed: {self.stats['processed']}")
        logger.info(f"   • Successful: {self.stats['successful']}")
        logger.info(f"   • Failed: {self.stats['failed']}")
        logger.info(f"   • Success rate: {(self.stats['successful'] / max(1, self.stats['processed']) * 100):.1f}%")

    async def _process_batch(self):
        """Process a batch of pending notifications."""
        async for session in get_async_session():
            try:
                service = NotificationService(session)

                # Process pending notifications
                results = await service.process_pending_notifications(limit=self.batch_size)

                # Update statistics
                processed = results["processed"]
                successful = results["successful"]
                failed = results["failed"]

                self.stats["processed"] += processed
                self.stats["successful"] += successful
                self.stats["failed"] += failed

                if processed > 0:
                    logger.info(f"📤 Processed {processed} notifications: {successful} successful, {failed} failed")

                # Clean up old notifications periodically
                await self._cleanup_old_notifications(service)

            except Exception as e:
                logger.error(f"❌ Error processing batch: {str(e)}")
                raise

            finally:
                await session.close()

    async def _cleanup_old_notifications(self, service: NotificationService):
        """Clean up old completed/failed notifications."""
        try:
            # Clean up notifications older than 30 days
            cutoff_date = datetime.now() - timedelta(days=30)

            # This would be implemented in the service
            # await service.cleanup_old_notifications(cutoff_date)

        except Exception as e:
            logger.warning(f"⚠️  Failed to cleanup old notifications: {str(e)}")


class NotificationScheduler:
    """Scheduler for time-based notifications."""

    def __init__(self, check_interval: int = 60):
        """
        Initialize the notification scheduler.

        Args:
            check_interval: Seconds between scheduled notification checks
        """
        self.check_interval = check_interval
        self.running = False

    async def start(self):
        """Start the notification scheduler."""
        self.running = True

        logger.info("⏰ Starting notification scheduler...")
        logger.info(f"   • Check interval: {self.check_interval}s")

        while self.running:
            try:
                await self._check_scheduled_notifications()

                if self.running:
                    await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"❌ Error in scheduler cycle: {str(e)}")
                await asyncio.sleep(self.check_interval)

    async def stop(self):
        """Stop the notification scheduler."""
        logger.info("🛑 Stopping notification scheduler...")
        self.running = False

    async def _check_scheduled_notifications(self):
        """Check for notifications that should be sent now."""
        async for session in get_async_session():
            try:
                service = NotificationService(session)

                # Check for booking reminders
                await self._process_booking_reminders(service)

                # Check for loyalty point expiration warnings
                await self._process_loyalty_reminders(service)

                # Check for waitlist expiration notifications
                await self._process_waitlist_expiration(service)

            except Exception as e:
                logger.error(f"❌ Error checking scheduled notifications: {str(e)}")
                raise

            finally:
                await session.close()

    async def _process_booking_reminders(self, service: NotificationService):
        """Process booking reminder notifications."""
        try:
            # This would check for bookings that need reminders
            # and queue the appropriate notifications

            # Example: Send reminders 24 hours, 2 hours, and 30 minutes before appointments
            reminder_times = [
                timedelta(hours=24),
                timedelta(hours=2),
                timedelta(minutes=30)
            ]

            for reminder_time in reminder_times:
                reminder_date = datetime.now() + reminder_time
                # Check for bookings at this time and send reminders
                # await service.send_booking_reminders(reminder_date)
                pass

        except Exception as e:
            logger.warning(f"⚠️  Failed to process booking reminders: {str(e)}")

    async def _process_loyalty_reminders(self, service: NotificationService):
        """Process loyalty point expiration reminders."""
        try:
            # Check for points expiring in 7 days and send warnings
            expiry_warning_date = datetime.now() + timedelta(days=7)
            # await service.send_points_expiry_warnings(expiry_warning_date)
            pass

        except Exception as e:
            logger.warning(f"⚠️  Failed to process loyalty reminders: {str(e)}")

    async def _process_waitlist_expiration(self, service: NotificationService):
        """Process waitlist expiration notifications."""
        try:
            # Check for waitlist entries that are about to expire
            # await service.send_waitlist_expiration_warnings()
            pass

        except Exception as e:
            logger.warning(f"⚠️  Failed to process waitlist expiration: {str(e)}")


# Global worker and scheduler instances
worker: Optional[NotificationWorker] = None
scheduler: Optional[NotificationScheduler] = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"📡 Received signal {signum}, initiating graceful shutdown...")

    async def shutdown():
        if worker:
            await worker.stop()
        if scheduler:
            await scheduler.stop()

    # Run shutdown in the event loop
    asyncio.create_task(shutdown())


async def main():
    """Main function to run the notification worker and scheduler."""
    global worker, scheduler

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Create worker and scheduler instances
        worker = NotificationWorker(
            batch_size=getattr(settings, 'NOTIFICATION_BATCH_SIZE', 50),
            sleep_interval=getattr(settings, 'NOTIFICATION_SLEEP_INTERVAL', 30)
        )

        scheduler = NotificationScheduler(
            check_interval=getattr(settings, 'NOTIFICATION_SCHEDULER_INTERVAL', 60)
        )

        # Start both worker and scheduler concurrently
        await asyncio.gather(
            worker.start(),
            scheduler.start()
        )

    except KeyboardInterrupt:
        logger.info("🔄 Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"❌ Worker failed: {str(e)}")
        sys.exit(1)
    finally:
        if worker:
            await worker.stop()
        if scheduler:
            await scheduler.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🔄 Shutdown complete.")
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        sys.exit(1)
