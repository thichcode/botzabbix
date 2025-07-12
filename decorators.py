import functools
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import Config

logger = logging.getLogger(__name__)

def admin_only(func):
    """Decorator to check if user is admin"""
    @functools.wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id not in Config.ADMIN_IDS:
            await update.message.reply_text("Bạn không có quyền sử dụng lệnh này.")
            logger.warning(f"Unauthorized access attempt by user {update.effective_user.id}")
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapper

def validate_input(max_length: int = 1000):
    """Decorator to validate user input"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if context.args:
                user_input = ' '.join(context.args)
                if len(user_input) > max_length:
                    await update.message.reply_text(f"Input quá dài. Tối đa {max_length} ký tự.")
                    return
                # Basic sanitization
                if any(char in user_input for char in ['<', '>', 'script', 'javascript']):
                    await update.message.reply_text("Input chứa ký tự không hợp lệ.")
                    return
            return await func(self, update, context, *args, **kwargs)
        return wrapper
    return decorator 