"""Central application state model for TestStandGUI.

ExecutionWindow is the application root controller, but long-lived state is kept
here so dialogs, future gRPC clients, result recovery, and reports can share one
consistent model without passing many independent variables around.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class ApplicationState:
    # Test profile / configuration
    loaded_profile: dict[str, Any] = field(default_factory=dict)
    profile_path: Optional[Path] = None
    loaded_for_run: bool = False

    # Machine/runtime state
    machine_state: str = "IDLE"
    machine_homed: bool = False

    # Run identity and results
    run_id: Optional[str] = None
    results_dir: Optional[Path] = None

    # Schedule and lifecycle timestamps
    test_start_datetime: Optional[datetime] = None
    estimated_complete_datetime: Optional[datetime] = None
    test_end_datetime: Optional[datetime] = None
    schedule_locked: bool = False
    last_schedule_minute: Optional[str] = None

    # Future runtime state fields
    current_cycle: int = 0
    total_cycles: int = 0
    active_faults: list[str] = field(default_factory=list)

    def load_profile(self, config: dict[str, Any], file_path: str | Path | None) -> None:
        """Load a new test profile and reset run-specific state.

        This should be called when the operator loads, creates, or modifies a
        test profile. It intentionally clears homing, run ID, results folder, and
        timestamps because those belong to a specific execution, not the profile.
        """
        self.loaded_profile = config or {}
        self.profile_path = Path(file_path) if file_path else None
        self.loaded_for_run = True

        self.machine_state = "IDLE"
        self.machine_homed = False

        self.run_id = None
        self.results_dir = None

        self.test_start_datetime = None
        self.estimated_complete_datetime = None
        self.test_end_datetime = None
        self.schedule_locked = False
        self.last_schedule_minute = None

        self.current_cycle = 0
        self.total_cycles = 0
        self.active_faults.clear()

    def clear_profile(self) -> None:
        """Return the application to a no-profile-loaded idle state."""
        self.loaded_profile = {}
        self.profile_path = None
        self.loaded_for_run = False
        self.machine_state = "IDLE"
        self.machine_homed = False
        self.run_id = None
        self.results_dir = None
        self.test_start_datetime = None
        self.estimated_complete_datetime = None
        self.test_end_datetime = None
        self.schedule_locked = False
        self.last_schedule_minute = None
        self.current_cycle = 0
        self.total_cycles = 0
        self.active_faults.clear()

    def set_preview_schedule(
        self,
        preview_start: datetime,
        run_id: str,
        estimated_complete: Optional[datetime],
        minute_key: str,
    ) -> None:
        """Update the pre-run rolling schedule preview.

        Before PRESS TO RUN, the dashboard previews the start time, Run ID, and
        estimated completion time. This preview rolls forward once per minute.
        Once the test starts, schedule_locked becomes True and this method should
        no longer be called.
        """
        if self.schedule_locked:
            return

        self.test_start_datetime = preview_start
        self.test_end_datetime = None
        self.run_id = run_id
        self.estimated_complete_datetime = estimated_complete
        self.last_schedule_minute = minute_key

    def lock_schedule(self, actual_start: datetime) -> None:
        """Lock schedule values when the operator starts the test."""
        self.schedule_locked = True
        self.test_start_datetime = actual_start
        self.test_end_datetime = None

    def mark_finished(self, finished_at: datetime) -> None:
        """Record the actual end time of a completed or aborted run."""
        self.schedule_locked = True
        self.test_end_datetime = finished_at

    def load_resume_state(
        self,
        run_id: str,
        results_dir: str | Path,
        test_start: Optional[datetime],
        test_end: Optional[datetime],
        estimated_complete: Optional[datetime],
    ) -> None:
        """Load persisted execution metadata from a previous incomplete run."""
        self.loaded_for_run = True
        self.schedule_locked = True
        self.run_id = run_id
        self.results_dir = Path(results_dir)
        self.test_start_datetime = test_start
        self.test_end_datetime = test_end
        self.estimated_complete_datetime = estimated_complete

    @property
    def has_profile(self) -> bool:
        return self.loaded_for_run and bool(self.loaded_profile)
