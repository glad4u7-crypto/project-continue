# User Guide

## Run the dashboard

1. Install Python 3.11 or newer.
2. Clone this repository and open its folder.
3. Create and activate a virtual environment.
4. Install packages: `pip install -r requirements.txt`.
5. Start the app: `streamlit run app.py`.
6. Open the local address printed by Streamlit in your browser. The layout is designed to work on mobile browsers too.

## Current functionality

The dashboard is an initial landing page. Project registration, task creation, automatic planning, and GitHub verification are planned capabilities and are not yet implemented.

## Optional GitHub configuration

Copy `.env.example` to `.env` and set only the values needed by the current application. Keep `.env` private; it is excluded by `.gitignore`. Never share a real access token in chat, screenshots, or source code.

## Project status

This is the initial foundation scaffold, not the complete Project Continue system. See [Development Guide](DEVELOPMENT.md) for development and checkpoint practices.
