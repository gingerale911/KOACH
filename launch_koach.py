import sys
import os
import traceback

log_file = r"c:\Users\aviji\Desktop\f1\launch_debug.log"

try:
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Starting launch_koach.py in {os.getcwd()}\n")
        f.write(f"sys.executable: {sys.executable}\n")
        f.write(f"sys.path: {sys.path}\n")

    os.chdir(r"c:\Users\aviji\Desktop\f1\KOACH")
    sys.path.insert(0, r"c:\Users\aviji\Desktop\f1\KOACH")

    from f1_coach.presentation.app import run
    run()
except Exception as e:
    with open(log_file, "a", encoding="utf-8") as f:
        f.write("Exception caught:\n")
        traceback.print_exc(file=f)
    sys.exit(1)
