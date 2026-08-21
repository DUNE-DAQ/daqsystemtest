#!/bin/env python3

# August 2026, KAB:  As part of developing functionality to support multiple user-specified
# applications running in our integration tests, I ran some web searches to learn more about
# how to start and receive output from multiple processes in Python.  The Python code that
# was suggested in the response was very helpful.
# I modified that sample code to start drunc-unified-shell, drunc-process-manager, and
# drunc-process-manager-shell processes.  The modified script was so helpful that I wanted
# to capture it for later use, and this is that script.
# I can imagine this script being used by non-run-control experts to learn about how the
# different RC apps interact, and maybe the script could be used to provide an easy way
# to start up a different set of applications.
# This code is far from production-ready.  So, if we ever decide to make it a general-purpose
# tool, we should improve various aspects of it.  The integrationtest/async_proc_mgmt
# code (which used this script as a starting point) might be useful when thinking about any
# possible improvements.
#
# The script can by run by typing 'multiprocess_runcontrol_driver.py' with no arguments.
# Once the script has been started, commands can be sent to one of the three processes by
# pre-pending the process nickname to the command (with a colon separator). For example, 'drunc:ps'.
# Typing 'exit' (with no process prefix) will exit the script.

import asyncio
import sys
import time
from daqconf.utils import find_free_port

last_msg_time = 0

async def read_stream(stream, process_name, completion_event):
    """Asynchronously reads lines from a stream and prints them immediately."""
    global last_msg_time
    while True:
        line = await stream.readline()
        if not line:
            break
        decoded_line = line.decode().rstrip()

        if "*** COMMAND HAS COMPLETED ***" in decoded_line:
            completion_event.set()
            continue

        # Decode and strip line endings
        print(f"[{process_name}] {line.decode().rstrip()}", flush=True)
        last_msg_time = time.time()

async def interactive_manager(commands):
    processes = {}
    tasks = []
    command_completion_event = asyncio.Event()
    global last_msg_time

    # 1. Start all interactive subprocesses
    for cmd in commands:
        name = cmd.pop(0)
        print()
        print(f"*** Starting \"{cmd[0]}\" with local process name \"{name}\"...")
        print()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        processes[name] = proc
        
        # 2. Schedule output reading tasks concurrently
        tasks.append(asyncio.create_task(read_stream(proc.stdout, name, command_completion_event)))

        time.sleep(2)

    print()
    print(f"*** Started {len(processes)} processes. Type: '<process_name>:<input>' (e.g., shell:help)")
    print("*** Type 'exit' to quit everything.")
    print()

    # 3. Handle interactive user input from the main terminal
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    try:
        while True:
            print("\nmprc_drvr> ", end="", flush=True)
            user_line = await reader.readline()
            if not user_line:
                break
                
            command_text = user_line.decode().strip()
            if command_text.lower() == 'exit':
                break

            # Parse target process and message (Format: Proc-1:your_command)
            if ":" in command_text:
                target, msg = command_text.split(":", 1)
                target = target.strip()
                
                if target in processes:
                    proc = processes[target]
                    if proc.returncode is None:  # Check if still running
                        cmd_start_time = time.time()
                        proc.stdin.write((msg + "\n").encode())
                        await proc.stdin.drain()
                        print(f"[System] Sent to {target}: {msg}")
                        if "drunc" in target:
                            proc.stdin.write(("echo '*** COMMAND HAS COMPLETED ***'\n").encode())
                            await proc.stdin.drain()
                            print(f"[System] Sent to {target}: echo '*** COMMAND HAS COMPLETED ***'")
                            await command_completion_event.wait()
                            command_completion_event.clear()
                        else:
                            now = time.time()
                            while True:
                                if last_msg_time <= cmd_start_time:
                                    if now - cmd_start_time > 5:
                                        break
                                else:
                                    if now - last_msg_time >= 5:
                                        break
                                await asyncio.sleep(0.25)
                                now = time.time()
                    else:
                        print(f"[System] Error: {target} has already exited.")
                else:
                    print(f"[System] Error: Process '{target}' not found.")
            else:
                print("[System] Invalid format. Use: <process_name>:<command>")

    except asyncio.CancelledError:
        pass
    finally:
        # 4. Cleanup and terminate remaining processes
        print("\n[System] Shutting down processes...")
        for name, proc in reversed(processes.items()):
            if proc.returncode is None:
                proc.terminate()
                await proc.wait()
        
        # Cancel background reading tasks
        for task in tasks:
            task.cancel()

if __name__ == "__main__":
    pm_port = find_free_port(50001, 52000)

    # This set of DUNE-DAQ control applications is the first useful one that came to mind.
    # It allows testing of process-manager-as-a-service and gives us a way to see how these
    # three run control programs interact.  Of course, there may be different sets of apps
    # that will be useful in the future.  At that time, we may want to simply edit the following
    # list to have different apps, or we may consider something more dynamic - to be decided.
    interactive_cmds = [
        ["pm", "drunc-process-manager", "ssh-standalone", str(pm_port)],
        ["pmshell", "drunc-process-manager-shell", f"grpc://localhost:{pm_port}"],
        ["drunc", "drunc-unified-shell", f"grpc://localhost:{pm_port}", "config/daqsystemtest/example-configs.data.xml", "local-1x1-config", "biery-local-test"]
    ]
    
    try:
        asyncio.run(interactive_manager(interactive_cmds))
    except KeyboardInterrupt:
        print("\n[System] Exited via Ctrl+C.")
