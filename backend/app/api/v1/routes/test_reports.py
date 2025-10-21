"""
Simple test to verify reporting endpoints are working.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict, Any

router = APIRouter(prefix="/test-reports", tags=["test-reports"])


@router.get("/health")
async def test_reports_health() -> Dict[str, Any]:
    """Test endpoint to verify reports module is working."""
    return {
        "status": "healthy",
        "module": "reports",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Reports endpoints are working"
    }


@router.get("/simple-metrics")
async def get_simple_metrics() -> Dict[str, Any]:
    """Simple metrics endpoint without database dependencies."""
    return {
        "total_bookings": 100,
        "completed_bookings": 85,
        "completion_rate": 85.0,
        "total_revenue": 5250.00,
        "period": "last_30_days",
        "generated_at": datetime.utcnow().isoformat()
    }
