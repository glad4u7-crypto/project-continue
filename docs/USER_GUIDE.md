# User Guide — Foundation

## Run the dashboard

1. Install Python 3.11 or newer.
2. Clone this repository and open its folder.
3. Create and activate a virtual environment.
4. Install packages: `pip install -r requirements.txt`.
5. Start the app: `streamlit run app.py`.
6. Open the local address printed by Streamlit in your browser. The layout is designed to work on mobile browsers too.

## What works in this phase

The dashboard provides the initial Project Continue landing page and reports whether a GitHub repository is configured. Project registration, task creation, automatic planning, and GitHub verification are future phases and are not implemented yet.

## Optional GitHub configuration

Copy `.env.example` to `.env` and set only the values you need. Keep `.env` private; it is excluded by `.gitignore`. Never share a real access token in chat, screenshots, or source code. The foundation dashboard does not need a GitHub token to start.

## Current status

This is the foundation release, not the complete autonomous agent. Use the development guide for the next implementation checkpoints.
