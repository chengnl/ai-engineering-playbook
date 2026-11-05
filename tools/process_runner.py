"""Bounded local process execution; graceful POSIX group shutdown then escalation."""
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def stop_process(process, grace):
    if sys.platform == 'win32':
        process.terminate()
        try:
            process.wait(timeout=grace)
            return 'terminated-direct-child'
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return 'killed-direct-child'
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait()
        return 'already-exited'
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        process.poll()  # Reap the leader while also waiting for descendants.
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            process.wait()
            return 'graceful'
        except PermissionError:
            # A denied liveness probe is not evidence of exit. Recheck only within
            # the existing grace; final signal denial still fails explicitly.
            pass
        time.sleep(min(0.05, max(0, deadline - time.monotonic())))
    try:
        os.killpg(process.pid, signal.SIGKILL)
        outcome = 'forced'
    except ProcessLookupError:
        outcome = 'graceful'
    process.wait()
    return outcome


def execute(command, project):
    started = utc_now()
    clock = time.monotonic()
    record = {'argv': command['argv'], 'started_at': started, 'returncode': None, 'termination': 'none'}
    try:
        process = subprocess.Popen(command['argv'], cwd=project, start_new_session=True)
    except OSError:
        record['result'] = 'start-failed'
    else:
        try:
            record['returncode'] = process.wait(timeout=command['timeout_seconds'])
            record['result'] = 'passed' if record['returncode'] == 0 else 'failed'
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            record['result'] = 'timed-out' if isinstance(error, subprocess.TimeoutExpired) else 'interrupted'
            try:
                record['termination'] = stop_process(process, command.get('grace_seconds', 3))
                record['returncode'] = process.returncode
            except OSError as failure:
                # Keep the run failed/unknown, but allow the reviewed cleanup and
                # residual hooks to run. Never infer remote/descendant termination.
                record.update(result='termination-failed', termination='unconfirmed',
                              termination_error=type(failure).__name__, returncode=process.poll())
    record.update(finished_at=utc_now(), duration_seconds=round(time.monotonic() - clock, 6))
    return record
