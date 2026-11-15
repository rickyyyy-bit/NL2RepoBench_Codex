"""Docker command transport shared by benchmark infrastructure."""
import subprocess


def docker_command(args, **kwargs):
    return subprocess.run(["docker", *args], check=True, text=True, **kwargs)
