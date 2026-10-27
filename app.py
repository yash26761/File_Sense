import os
import subprocess
import sys
import threading
from flask import Flask, jsonify, render_template, request
from scanner import scan_folder, find_duplicates
from analyzer import analyze_files

app = Flask(__name__)

# Mutex to ensure single-instance folder dialog access and prevent concurrent dialog conflicts
_browse_lock = threading.Lock()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/browse", methods=["POST"])
def api_browse():
    """
    Opens a native Windows folder browser dialog using Python's built-in tkinter.filedialog.
    Returns the chosen folder path or cancellation status as JSON.
    
    Windows GUI / Threading Architecture:
      Flask processes incoming HTTP requests in worker threads. Initializing and destroying
      Tcl/Tk (tkinter) across secondary threads on Windows triggers the known fatal C-level assertion:
      'Tcl_AsyncDelete: async handler deleted by the wrong thread'.
      To overcome this, the dialog is launched via sys.executable in an isolated subprocess,
      ensuring Tcl runs on its own main thread while safely returning the chosen path to the caller.
    """
    if not _browse_lock.acquire(blocking=False):
        return jsonify({
            "success": False,
            "error": "A folder selection dialog is already open."
        }), 409

    try:
        dialog_script = (
            "import os, sys\n"
            "try:\n"
            "    import tkinter as tk\n"
            "    from tkinter import filedialog\n"
            "except ImportError:\n"
            "    sys.exit(3)\n"
            "try:\n"
            "    root = tk.Tk()\n"
            "    root.withdraw()\n"
            "    root.attributes('-topmost', True)\n"
            "    root.focus_force()\n"
            "    chosen = filedialog.askdirectory(parent=root, title='FileSense - Select Folder to Scan', mustexist=True)\n"
            "    root.destroy()\n"
            "    if chosen:\n"
            "        print(os.path.normpath(chosen))\n"
            "except Exception as e:\n"
            "    sys.stderr.write(str(e))\n"
            "    sys.exit(1)\n"
        )

        proc = subprocess.run(
            [sys.executable, "-c", dialog_script],
            capture_output=True,
            text=True,
            timeout=120
        )

        if proc.returncode == 3:
            return jsonify({
                "success": False,
                "error": "Tkinter GUI framework is not available in the Python runtime."
            }), 501

        if proc.returncode != 0:
            err_msg = proc.stderr.strip() or "Native dialog closed unexpectedly."
            return jsonify({
                "success": False,
                "error": f"Folder dialog failed: {err_msg}"
            }), 500

        selected_directory = proc.stdout.strip()

        if not selected_directory:
            return jsonify({
                "success": True,
                "cancelled": True,
                "folder_path": None
            }), 200

        return jsonify({
            "success": True,
            "cancelled": False,
            "folder_path": selected_directory
        }), 200

    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "error": "Folder selection dialog timed out after 120 seconds. Please try again."
        }), 408

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to open native folder dialog: {str(e)}"
        }), 500

    finally:
        _browse_lock.release()


@app.route("/api/scan", methods=["POST"])
def api_scan():
    if not request.is_json:
        return jsonify({"success": False, "error": "Request body must be JSON."}), 400

    data = request.get_json(silent=True) or {}
    folder_path = data.get("folder_path")

    if not folder_path or not isinstance(folder_path, str) or not folder_path.strip():
        return jsonify({"success": False, "error": "Please provide a valid folder path string."}), 400

    clean_path = folder_path.strip()

    try:
        # Step 1: Recursively scan folder
        scan_result = scan_folder(clean_path)

        # If a fatal error occurred preventing directory access (0 files and fatal error)
        if scan_result.get("errors") and scan_result.get("total_files", 0) == 0:
            return jsonify({
                "success": False,
                "error": "; ".join(scan_result["errors"]),
                "folder_path": scan_result.get("folder_path", clean_path)
            }), 400

        files = scan_result.get("files", [])

        # Step 2: Detect duplicate file groups
        duplicate_results = find_duplicates(files)

        # Step 3: Run PySpark analysis
        analysis_results = analyze_files(files, duplicate_results=duplicate_results, stop_session=False)

        # Collect unique non-fatal warnings
        warnings = list(dict.fromkeys(
            scan_result.get("errors", []) + duplicate_results.get("errors", [])
        ))

        return jsonify({
            "success": True,
            "folder_path": scan_result.get("folder_path", clean_path),
            "total_files": analysis_results.get("total_files", 0),
            "total_size": analysis_results.get("total_size", 0),
            "duplicate_group_count": analysis_results.get("duplicate_group_count", 0),
            "total_duplicate_files": analysis_results.get("total_duplicate_files", 0),
            "recoverable_bytes": analysis_results.get("recoverable_bytes", 0),
            "extension_summary": analysis_results.get("extension_summary", []),
            "top_10_largest": analysis_results.get("top_10_largest", []),
            "duplicate_groups": duplicate_results.get("duplicate_groups", []),
            "files": files,
            "warnings": warnings
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": f"Internal scan error: {str(e)}"}), 500



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8502, debug=False, use_reloader=False)

