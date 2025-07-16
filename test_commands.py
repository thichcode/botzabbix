import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import importlib
import os

COMMANDS_DIR = "commands"

class TestAllCommands(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.command_files = [
            f for f in os.listdir(COMMANDS_DIR)
            if f.endswith(".py") and f != "__init__.py"
        ]

    async def test_all_commands(self):
        for file in self.command_files:
            module_name = f"{COMMANDS_DIR}.{file[:-3]}"
            module = importlib.import_module(module_name)
            # Tìm class có tên dạng PascalCase + Command
            class_name = "".join([part.capitalize() for part in file[:-3].split("_")]) + "Command"
            if hasattr(module, class_name):
                CommandClass = getattr(module, class_name)
                cmd = CommandClass()
                update = MagicMock()
                update.message.reply_text = AsyncMock()
                update.message.reply_photo = AsyncMock()
                context = MagicMock()
                context.args = ["host1", "system.cpu.util", "1200"]
                # Chỉ patch nếu module có get_zabbix_api
                if hasattr(module, "get_zabbix_api"):
                    with patch(f"{module_name}.get_zabbix_api", return_value=self.mock_zabbix_api()):
                        try:
                            await cmd.execute(update, context)
                        except Exception as e:
                            self.fail(f"{class_name}.execute() raised {e}")
                else:
                    try:
                        await cmd.execute(update, context)
                    except Exception as e:
                        self.fail(f"{class_name}.execute() raised {e}")

    def mock_zabbix_api(self):
        mock_zapi = MagicMock()
        mock_zapi.host.get.return_value = [{"hostid": "10101"}]
        mock_zapi.item.get.return_value = [{"itemid": "20202", "name": "CPU Util"}]
        mock_zapi.history.get.return_value = [
            {"clock": "1718000000", "value": "10"},
            {"clock": "1718000600", "value": "20"},
        ]
        # Có thể mở rộng cho các API khác nếu cần
        return mock_zapi

if __name__ == '__main__':
    unittest.main() 