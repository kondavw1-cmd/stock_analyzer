# 🚀 `uv` Reference Guide & Workflow Commands

This document serves as the official reference guide for managing dependencies, environments, and execution workflows using **`uv`** in your portfolio analyzer pipeline.

---

## 1. Installation & Setup

If you need to install or update `uv` on a new machine or cloud runner:

* **Windows (PowerShell):**
  ```powershell
  powershell -c "irm https://astral.sh/uv/install.sh | iex"
  ```
* **Check Version:**
  ```bash
  uv --version
  ```

---

## 2. Environment & Project Initialization

* **Initialize a New Project (creates `pyproject.toml`):**
  ```bash
  uv init --app
  ```
* **Create a Virtual Environment (`.venv`):**
  ```bash
  uv venv
  ```
* **Activate the Virtual Environment:**
  * *Windows (PowerShell):* `.venv\Scripts\Activate.ps1`

---

## 3. Dependency Management (Modern Workflow)

Using `uv` with lockfile management (`pyproject.toml` and `uv.lock`):

* **Add Packages:**
  ```bash
  uv add pandas yfinance streamlit supabase google-api-python-client google-auth-oauthlib openpyxl
  ```
* **Remove Packages:**
  ```bash
  uv remove package_name
  ```
* **Sync Environment with Lockfile (Ideal for CI/CD & GitHub Actions):**
  Installs exact versions specified in `uv.lock`.
  ```bash
  uv sync
  ```
* **Strict Frozen Sync (Fails if lockfile is out of sync—great for cloud runners):**
  ```bash
  uv sync --frozen
  ```

---

## 4. Legacy / `requirements.txt` Workflow

If working with a traditional `requirements.txt` layout:

* **Install from `requirements.txt`:**
  ```bash
  uv pip install -r requirements.txt
  ```
* **Generate/Export `requirements.txt` from Lockfile:**
  ```bash
  uv pip compile pyproject.toml -o requirements.txt
  ```

uv pip sync requirements.txt

---

## 5. Running Code & Scripts

* **Run a Python Script using the Environment:**
  `uv run` automatically ensures your virtual environment is active and up to date before executing.
  ```bash
  uv run main.py
  ```
* **Run any CLI tool inside the environment without manual activation:**
  ```bash
  uv run streamlit run app.py
  ```

---

## 6. Maintenance & Troubleshooting

* **Clear Global Cache (frees up disk space if needed):**
  ```bash
  uv cache clean
  ```
* **Check Environment Info & Python Path:**
  ```bash
  uv pip tree
  ```