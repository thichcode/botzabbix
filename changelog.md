# Changelog

## [Unreleased] - 2025-07-14

### Bot v2.0 - Telebot Implementation / Triển khai Bot v2.0 với Telebot

- **New Bot Version:**
  - Created `botv2.py` using `pyTelegramBotAPI` (telebot) library
  - Added `run_botv2.py` script for easy bot v2 execution
  - Updated `requirements.txt` to include `pyTelegramBotAPI==4.15.4`
  - Enhanced features with state management and inline keyboards
  - Improved error handling and user experience

- **Enhanced Features in Bot v2:**
  - **State Management:** Conversation flow management for multi-step interactions
  - **Inline Keyboards:** Interactive button selection for graph items
  - **Better Error Handling:** Improved error messages and recovery mechanisms
  - **Simplified API:** Easier to use and maintain compared to python-telegram-bot
  - **Consistent Commands:** All commands from bot v1 with improved implementation

- **Command Improvements:**
  - `/getalerts` - Renamed from `/getproblems` for clarity
  - `/gethosts` - Renamed from `/hosts` for consistency
  - `/addwebsite` - New command for adding websites to screenshot list
  - Enhanced `/getgraph` with interactive inline keyboard selection
  - Improved callback handling for graph selection

- **Documentation Updates:**
  - Updated `README.md` with bot v2 information and usage instructions
  - Added comparison between bot v1 and bot v2 features
  - Updated installation instructions for both bot versions

### Security Enhancements / Cải thiện bảo mật

- **Sensitive Data Masking:**
  - Added automatic masking of sensitive information in logs (tokens, passwords, API keys)
  - Implemented `SensitiveDataFilter` class to filter all log messages
  - Created `mask_sensitive_data()` function with support for multiple patterns
  - Added `setup_secure_logging()` function to configure secure logging globally
  - Updated `Config` class with `get_safe_config_info()` method for safe configuration display

- **Logging Security:**
  - All log messages now automatically mask sensitive data before being written
  - Support for Telegram Bot Token masking (format: 123456789:*****)
  - Support for API key masking (various formats)
  - Support for password masking (multiple patterns)
  - Support for general token masking
  - Support for Zabbix token masking
  - Safe for production environments

- **Zabbix Authentication Enhancement:**
  - Added support for Zabbix API Token authentication (Zabbix 5.4+)
  - Priority: Use API token if available, fallback to username/password
  - Only dashboard screenshot requires username/password for web interface login
  - All API calls now use token authentication when available
  - Improved security by reducing dependency on username/password

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
  - Added `/start` command to show welcome message and available commands
  - Added `/help` command to show detailed usage guide
  - Commands now show different content for admin vs regular users
