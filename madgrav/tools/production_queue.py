"""
Production Queue & Workshop Kiosk Mode Manager for MadGrav.
Manages batch manufacturing queues, barcode job lookup, and daily output metrics.
"""

import time
import uuid


class ProductionQueueManager:
    """Batch job queue manager for workshop and kiosk production."""

    def __init__(self):
        self.queue = []
        self.completed_jobs = []

    def add_job(self, job_name, file_path, quantity=1, priority=1, barcode=None):
        """Enqueue a new job for manufacturing."""
        job_id = str(uuid.uuid4())[:8]
        if not barcode:
            barcode = f"JOB-{job_id.upper()}"

        job = {
            "id": job_id,
            "name": job_name,
            "file_path": file_path,
            "quantity": quantity,
            "priority": priority,
            "barcode": barcode,
            "status": "queued",
            "added_at": time.time()
        }
        self.queue.append(job)
        self.queue.sort(key=lambda j: j["priority"], reverse=True)
        return job

    def get_next_job(self):
        """Fetch highest-priority pending job."""
        pending = [j for j in self.queue if j["status"] == "queued"]
        if pending:
            job = pending[0]
            job["status"] = "in_progress"
            return job
        return None

    def mark_job_completed(self, job_id, duration_sec):
        """Mark a job as finished and record production stats."""
        for j in self.queue:
            if j["id"] == job_id:
                j["status"] = "completed"
                j["duration_sec"] = duration_sec
                j["completed_at"] = time.time()
                self.completed_jobs.append(j)
                return True
        return False

    def lookup_job_by_barcode(self, barcode_string):
        """Retrieve job matching scanned barcode."""
        for j in self.queue:
            if j["barcode"] == barcode_string:
                return j
        return None

    def export_production_summary(self):
        """Return workshop metrics summary."""
        total_time = sum(j.get("duration_sec", 0.0) for j in self.completed_jobs)
        total_parts = sum(j.get("quantity", 1) for j in self.completed_jobs)
        return {
            "queued_count": len([j for j in self.queue if j["status"] == "queued"]),
            "completed_count": len(self.completed_jobs),
            "total_parts_produced": total_parts,
            "total_run_time_sec": round(total_time, 1),
            "avg_part_time_sec": round(total_time / total_parts, 1) if total_parts > 0 else 0.0
        }
