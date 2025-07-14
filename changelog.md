# Changelog

## [Unreleased] - 2025-07-14

### Refactoring

- **Modularization:**
  - Refactored the main `bot.py` file to be more streamlined and focused on bot initialization.
  - Moved database-related functions to a dedicated `db.py` module, improving data access logic and separation of concerns.
  - Extracted screenshot functionality into a `screenshot.py` module, which now includes improved error handling and retry mechanisms.
  - Created a `utils.py` module for common helper functions, such as URL extraction and validation, reducing code duplication.
  - Reorganized all command handlers into a `commands` directory, with each command in its own file, making the codebase more organized and easier to navigate.

- **Code Quality and Consistency:**
  - Standardized Zabbix API interactions by ensuring all calls go through the `zabbix.py` module.
  - Improved error handling across the application by replacing `print` statements with structured logging and adding more specific exception handling.
  - Enhanced the database module with context managers for safer connection handling and more robust error management.
  - Updated command modules to use the new modular structure, resulting in cleaner and more maintainable code.

- **Configuration and Execution:**
  - Centralized all configuration in the `config.py` module, which now includes validation to ensure all required environment variables are set.
  - Simplified the main execution script `run_bot.py` to call the `main` function from the refactored `bot.py`.

- **New Features:**
  - Added a `changelog.md` to track changes and new features over time.
