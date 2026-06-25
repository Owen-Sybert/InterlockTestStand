import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from utils.storedDataPaths import getSavedTestsDir


MAX_TEST_NAME_FILENAME_LENGTH = 50


def save_to_json(data):
    normalized_data = normalize_test_data(data)

    base_name = build_file_base_name(normalized_data)

    file_path = generate_safe_filename(
        getSavedTestsDir(),
        base_name
    )

    with open(file_path, "w") as f:
        json.dump(normalized_data, f, indent=4)

    return file_path


def normalize_test_data(data):
    def to_float(value):
        if value in ("", None):
            return None
        return float(value)

    def to_int(value):
        if value in ("", None):
            return None
        return int(value)

    def has_servo_settings(servo_num):
        keys = [
            f"servo{servo_num}_dwell_lower",
            f"servo{servo_num}_dwell_upper",
            f"servo{servo_num}_velocity",
            f"servo{servo_num}_acceleration",
        ]

        return any(data.get(key) not in ("", None) for key in keys)

    created_timestamp = datetime.now().replace(microsecond=0).isoformat()

    normalized = {
        "schema_version": 1,

        "test_metadata": {
            "test_id": str(uuid.uuid4()),
            "test_type": data.get("test_type", "").upper(),
            "test_name": data.get("test_name", "").strip(),
            "operator": data.get("operator", "").strip(),
            "dut_serial_number": data.get("dut_serial_number", "").strip(),
            "project_number": data.get("project_number", "").strip(),
            "notes": data.get("notes", "").strip(),
            "created_timestamp": created_timestamp,
        },

        "test_parameters": {
            "motion_profile_version": to_int(data.get("motion_profile_version", 1)) or 1,

            "cycle_time_sec": to_float(
                data.get("cycle_time")
            ),

            "make_and_carry_time_sec": to_float(
                data.get("make_and_carry_time")
            ),

            "number_of_cycles": to_int(
                data.get("number_of_cycles")
            ),

            "servos": []
        },

        "image_capture": {
            "enabled": data.get(
                "images_enabled", "No"
            ).lower() == "yes",

            "frequency_cycles": to_int(
                data.get("image_frequency")
            )
        },

        "logging": {
            "enabled": data.get(
                "logging_enabled", "Yes"
            ).lower() == "yes",

            "log_level": data.get(
                "log_level", "INFO"
            ).upper(),

            "telemetry_frequency_hz": to_float(
                data.get("telemetry_frequency_hz", 10)
            )
        },

        "execution": {
            "status": "NOT_RUN",
            "start_time": None,
            "end_time": None,
            "result": None
        }
    }

    for servo_num in range(1, 5):
        normalized["test_parameters"]["servos"].append(
            {
                "id": servo_num,

                "enabled": has_servo_settings(servo_num),

                "dwell_lower_sec": to_float(
                    data.get(f"servo{servo_num}_dwell_lower")
                ),

                "dwell_upper_sec": to_float(
                    data.get(f"servo{servo_num}_dwell_upper")
                ),

                "velocity": to_float(
                    data.get(f"servo{servo_num}_velocity")
                ),

                "acceleration": to_float(
                    data.get(f"servo{servo_num}_acceleration")
                )
            }
        )

    return normalized


def build_file_base_name(normalized_data):
    date_part = get_date_based_name()

    test_name = (
        normalized_data
        .get("test_metadata", {})
        .get("test_name", "")
        .strip()
    )

    if not test_name:
        return date_part

    safe_test_name = sanitize_filename(test_name)

    if safe_test_name:
        return f"{date_part} - {safe_test_name}"

    return date_part


def sanitize_filename(name):
    name = name.strip()

    # Replace characters that are invalid in Windows filenames.
    name = re.sub(r'[<>:"/\\|?*]', "_", name)

    # Replace repeated whitespace with a single space.
    name = re.sub(r"\s+", " ", name)

    # Remove trailing periods/spaces, which Windows does not like.
    name = name.rstrip(" .")

    return name[:MAX_TEST_NAME_FILENAME_LENGTH]


def generate_safe_filename(directory, base_name):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    file_path = directory / f"{base_name}.json"

    counter = 1

    while file_path.exists():
        file_path = directory / f"{base_name} ({counter}).json"
        counter += 1

    return file_path


def get_date_based_name():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")