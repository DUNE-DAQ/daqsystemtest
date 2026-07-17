#!/bin/env python3

import asyncio
import sys
import time
from daqconf.utils import find_free_port

async def read_stream(stream, process_name):
    """Asynchronously reads lines from a stream and prints them immediately."""
    while True:
        line = await stream.readline()
        if not line:
            break
        # Decode and strip line endings
        print(f"[{process_name}] {line.decode().rstrip()}", flush=True)

async def interactive_manager(commands):
    processes = {}
    tasks = []

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
        tasks.append(asyncio.create_task(read_stream(proc.stdout, name)))

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
                        proc.stdin.write((msg + "\n").encode())
                        await proc.stdin.drain()
                        print(f"[System] Sent to {target}: {msg}")
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

    interactive_cmds = [
        ["pm", "drunc-process-manager", "ssh-standalone", str(pm_port)],  # Launch Interactive Python Instance 1
        ["pmshell", "drunc-process-manager-shell", f"grpc://localhost:{pm_port}"],  # Launch Interactive Python Instance 2
        ["drunc", "drunc-unified-shell", f"grpc://localhost:{pm_port}", "config/daqsystemtest/example-configs.data.xml", "local-1x1-config", "biery-local-test"]   # Launch Interactive Python Instance 3
    ]
    
    try:
        asyncio.run(interactive_manager(interactive_cmds))
    except KeyboardInterrupt:
        print("\n[System] Exited via Ctrl+C.")
