# Uma Club Manager

Uma Club Manager is a Flask-based web application and CLI tool designed to help manage club members, track fan point progress, and automatically report status via Discord webhooks.

## Features
- **Member Management**: Track members' in-game IDs, names, and Discord information. Support for setting requirement exemptions and custom extra point requirements.
- **Data Synchronization**: Synchronize member data with Firebase, with local SQLite fallback and backups.
- **Fan Data Tracking**: Upload monthly CSV files containing fan progress to track members over time.
    - (Get data from Chrono Genesis, I can't automate it yet)
- **Dynamic Quotas**: Set configurable fan quotas based on specific daily requirements during different segments of the month.
- **Discord Integration**: Generates and sends detailed fan progress reports directly to a Discord webhook, pinging members whose status is "Awful" so they know they are falling behind.
- **CLI Utility**: Directly send Discord reports from the terminal to facilitate cron jobs or automation.

## Requirements
See `requirements.txt` for the full list of dependencies.

## Installation
1. Clone the repository to your local machine.
2. (Optional but recommended) Create and activate a virtual environment.
   ```bash
   # Linux/Mac
   python -m venv venv
   source venv/bin/activate
   ```
   ```powershell
   # Windows powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```
   ```powershell
   # Windows cmd
   python -m venv venv
   venv\Scripts\activate.bat
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `example.env` to `.env` and fill in your Discord Webhook URL:
   ```env
   DISCORD_WEBHOOK=YOUR_DISCORD_WEBHOOK
   ```
5. If using Firebase, ensure you place your `firebase_credentials.json` in the root of the project. If not provided, the application will fallback to using a local SQLite database (`backup.db`).

## Usage

### Web Application
Start the Flask development server:
```bash
python app.py
```
Then navigate to `http://localhost:5000` in your web browser. From the web interface, you can manage members, define fan requirements, upload monthly CSV data, and click to send reports to Discord.

### CLI Utility
You can send ad-hoc or scheduled Discord fan progress reports from the terminal using the CLI utility:
```bash
python util.py report [-h] [-m MONTH] [-y YEAR] [--missing]
```

**Examples:**
- Send a report for a specific month and year:
  ```bash
  python util.py report -m 03 -y 2026
  ```
- Send a report for the most recent month data available:
  ```bash
  python util.py report
  ```
- Include IDs in the report even if they are not linked in the member database:
  ```bash
  python util.py report --missing
  ```

## Project Structure
- `app.py`: The main Flask web application containing all routes.
- `util.py`: Core logic for calculating fan requirements/deficits and the CLI commands.
- `discord_bot.py`: Formatting and networking logic for sending chunked Discord webhook messages.
- `fan_data/`: Directory where uploaded CSV fan data is stored.
- `templates/` & `static/`: HTML templates and assets for the Web UI.
