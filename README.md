# FileSense 📁🔍

**FileSense** is an intelligent, high-performance storage analytics and file deduplication dashboard built with **Flask** and **PySpark**. It provides deep visibility into storage utilization, categorizes files across system drives, and surfaces exact duplicate files through optimized multi-stage hash sampling.

---

## 🌟 Key Features

- **🚀 Native Windows Folder Selection**: Seamless folder picker modal powered by an isolated background process to prevent Tkinter thread conflicts on Windows.
- **⚡ Dual-Engine Scanning**:
  - **PySpark Engine**: Leverages distributed Spark DataFrames for high-throughput scanning and aggregation across massive directory hierarchies.
  - **Fallback Python Engine**: Native Python fallback with multi-threaded directory traversal for systems without active Spark/Java runtimes.
- **🎯 Multi-Stage Duplicate Detection**:
  - Size pre-filtering (instant grouping by exact byte size).
  - Partial header & footer chunk hashing (quick verification).
  - Full SHA-256 validation for confirmed duplicate clusters.
- **📊 Interactive Visual Analytics**:
  - Category breakdown (Documents, Media, Code, Archives, etc.).
  - Largest files identification with direct file path inspection.
  - Duplicate groups inspection with potential recoverable storage calculations.
- **🎨 Modern Dark Dashboard**: Sleek, glassmorphism UI with responsive stats counters, charts, and real-time progress states.

---

## 📁 Project Structure

```text
FileSense/
│
├── app.py                  # Flask web server & API endpoints
├── scanner.py              # Directory traversal & multi-stage duplicate detection
├── analyzer.py             # PySpark / Python storage aggregation and category analytics
├── requirements.txt        # Python package dependencies
│
├── templates/
│   └── index.html          # Dashboard HTML template
│
├── static/
│   ├── style.css           # Modern dark UI design & styling
│   └── script.js           # Client-side state, API calls, and chart rendering
│
└── FileSense_Demo_Data/    # Mock dataset for quick testing and demonstration
```

---

## 🛠️ Getting Started

### Prerequisites

- **Python 3.10+**
- *(Optional for PySpark mode)* **Java 8, 11, or 17** (for Apache Spark engine)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/FileSense.git
   cd FileSense
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   # On Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Running FileSense

Start the web application:

```bash
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

Select any folder on your disk (or test with the included `FileSense_Demo_Data` directory) to run storage analysis and duplicate detection.

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
