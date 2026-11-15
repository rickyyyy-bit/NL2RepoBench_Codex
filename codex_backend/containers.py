"""Owned-container variant of the fork's batch helper.

The original helper force-removes by name even when create fails. This adapter
uses an exclusive Docker cidfile and only removes the ID created by this call.
Logs are retained in the task run directory and redacted by the runner.
"""
import json
from pathlib import Path
import re
import subprocess
import time
import uuid

from docker_self.batch_container import docker_command


def run_container(create_args, name, directory, timeout_seconds, env=None):
    started = time.monotonic()
    directory = Path(directory)
    cidfile = directory / "container.cid"
    if cidfile.exists():
        raise FileExistsError("Refusing to reuse a container cidfile")
    paths = {"stdout_path": directory / "stdout.jsonl", "stderr_path": directory / "stderr.log",
             "container_log_path": directory / "container.log"}
    result = {"container_name": name, "exit_code": None, "generation_status": "error", **{key: str(value) for key, value in paths.items()}}
    owned_id = None
    with paths["container_log_path"].open("x", encoding="utf-8") as lifecycle:
        try:
            # Docker refuses an existing cidfile. Only a successful create writes
            # a complete container ID; a name conflict cannot grant ownership.
            for retry in range(5):
                try:
                    created = docker_command(["create", "--cidfile", str(cidfile), "--name", name, *create_args],
                                             env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
                    lifecycle.write(created.stderr or "")
                    break
                except subprocess.CalledProcessError as exc:
                    lifecycle.write(exc.stderr or "")
                    if "already in use" not in (exc.stderr or "") or retry == 4:
                        raise
                    if cidfile.exists():
                        if cidfile.read_text().strip():
                            raise  # unexpected ownership state: never retry over it
                        cidfile.unlink()  # only our newly created, empty cidfile
                    name = "codex-retry-" + uuid.uuid4().hex
                    result["container_name"] = name
            owned_id = cidfile.read_text().strip()
            if not re.fullmatch(r"[a-f0-9]{64}", owned_id):
                owned_id = None
                raise ValueError("Docker did not return a valid owned container ID")
            result["container_id"] = owned_id
            with paths["stdout_path"].open("x", encoding="utf-8") as out, paths["stderr_path"].open("x", encoding="utf-8") as err:
                try:
                    attached = subprocess.run(["docker", "start", "--attach", owned_id], stdout=out, stderr=err, timeout=timeout_seconds)
                    result["attach_exit_code"] = attached.returncode
                except subprocess.TimeoutExpired:
                    result.update(generation_status="timeout", error=f"Execution exceeded {timeout_seconds} seconds")
                    docker_command(["stop", "--time", "10", owned_id], stdout=lifecycle, stderr=lifecycle, timeout=25)
            inspected = docker_command(["inspect", owned_id], stdout=subprocess.PIPE, stderr=lifecycle, timeout=30)
            state = json.loads(inspected.stdout)[0]["State"]
            if not state["Running"]:
                result["exit_code"] = state["ExitCode"]
            if result["generation_status"] != "timeout":
                success = (state["Status"] == "exited" and state["ExitCode"] == 0 and not state.get("OOMKilled")
                           and not state.get("Error") and result.get("attach_exit_code") == 0)
                result["generation_status"] = "completed" if success else "failed"
            if state.get("OOMKilled"):
                result["error"] = "Container was killed by the out-of-memory killer"
            elif state.get("Error"):
                result["error"] = state["Error"]
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            result["error"] = f"Container operation failed ({type(exc).__name__}); see container.log"
        finally:
            # Creation can finish while the Docker client times out. Recover only
            # from this invocation's cidfile, never from a globally shared name.
            if owned_id is None and cidfile.exists():
                candidate = cidfile.read_text().strip()
                owned_id = candidate if re.fullmatch(r"[a-f0-9]{64}", candidate) else None
            if owned_id:
                try:
                    removed = subprocess.run(["docker", "rm", "--force", owned_id], stdout=lifecycle, stderr=lifecycle, timeout=30)
                    if removed.returncode:
                        result["cleanup_error"] = "Owned container removal failed; see container.log"
                except (OSError, subprocess.SubprocessError) as exc:
                    result["cleanup_error"] = f"Owned container removal failed ({type(exc).__name__})"
            result["duration_seconds"] = round(time.monotonic() - started, 3)
    return result
