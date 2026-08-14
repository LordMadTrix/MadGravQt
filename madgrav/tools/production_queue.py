import time
import uuid
from typing import Optional, List, Dict, Any


class ProductionJob:
    """Represents a laser manufacturing job routed to a specific machine."""

    def __init__(
        self,
        name: str,
        file_path: str = "",
        target_machine_id: str = "laser_default",
        quantity: int = 1,
        priority: int = 1,
        estimated_sec: float = 60.0,
        barcode: Optional[str] = None,
        job_id: Optional[str] = None,
        status: str = "En attente",
    ):
        self.job_id = job_id or str(uuid.uuid4())[:8]
        self.id = self.job_id
        self.name = name
        self.file_path = file_path
        self.target_machine_id = target_machine_id
        self.quantity = quantity
        self.priority = priority
        self.estimated_sec = estimated_sec
        self.barcode = barcode or f"JOB-{self.job_id.upper()}"
        self.status = status
        self.added_at = time.time()
        self.completed_at = None
        self.duration_sec = 0.0

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.job_id,
            "job_id": self.job_id,
            "name": self.name,
            "file_path": self.file_path,
            "target_machine_id": self.target_machine_id,
            "quantity": self.quantity,
            "priority": self.priority,
            "barcode": self.barcode,
            "status": self.status,
            "estimated_sec": self.estimated_sec,
            "duration_sec": self.duration_sec,
            "added_at": self.added_at,
            "completed_at": self.completed_at,
        }


class ProductionQueueManager:
    """Batch job queue manager for multi-machine laser production."""

    def __init__(self):
        self.jobs: List[ProductionJob] = []
        self.completed_jobs: List[ProductionJob] = []

    @property
    def queue(self) -> List[ProductionJob]:
        return self.jobs

    def add_job(
        self,
        job_name: str,
        file_path: str = "",
        target_machine_id: str = "laser_default",
        quantity: int = 1,
        priority: int = 1,
        estimated_sec: float = 60.0,
        barcode: Optional[str] = None,
    ) -> ProductionJob:
        """Enqueue a new job for manufacturing."""
        job = ProductionJob(
            name=job_name,
            file_path=file_path,
            target_machine_id=target_machine_id,
            quantity=quantity,
            priority=priority,
            estimated_sec=estimated_sec,
            barcode=barcode,
        )
        self.jobs.append(job)
        self.jobs.sort(key=lambda j: j.priority, reverse=True)
        return job

    def get_jobs_for_machine(self, machine_id: str) -> List[ProductionJob]:
        """Fetch all queued jobs assigned to a specific laser machine."""
        return [j for j in self.jobs if j.target_machine_id == machine_id]

    def get_next_job(self, machine_id: Optional[str] = None) -> Optional[ProductionJob]:
        """Fetch highest-priority pending job."""
        for job in self.jobs:
            if job.status in ("queued", "En attente"):
                if machine_id is None or job.target_machine_id == machine_id:
                    job.status = "En cours"
                    return job
        return None

    def update_job_status(self, job_id: str, status: str) -> bool:
        """Update status of a specific job."""
        for j in self.jobs:
            if j.job_id == job_id or j.id == job_id:
                j.status = status
                return True
        return False

    def mark_job_completed(self, job_id: str, duration_sec: float) -> bool:
        """Mark a job as finished and record production stats."""
        for j in self.jobs:
            if j.job_id == job_id or j.id == job_id:
                j.status = "Terminé"
                j.duration_sec = duration_sec
                j.completed_at = time.time()
                self.completed_jobs.append(j)
                return True
        return False

    def lookup_job_by_barcode(self, barcode_string: str) -> Optional[ProductionJob]:
        """Retrieve job matching scanned barcode."""
        for j in self.jobs:
            if j.barcode == barcode_string:
                return j
        return None

    def export_production_summary(self) -> Dict[str, Any]:
        """Return workshop metrics summary."""
        total_time = sum(j.duration_sec for j in self.completed_jobs)
        total_parts = sum(j.quantity for j in self.completed_jobs)
        return {
            "queued_count": len([j for j in self.jobs if j.status in ("queued", "En attente")]),
            "completed_count": len(self.completed_jobs),
            "total_parts_produced": total_parts,
            "total_run_time_sec": round(total_time, 1),
            "avg_part_time_sec": round(total_time / total_parts, 1) if total_parts > 0 else 0.0,
        }

