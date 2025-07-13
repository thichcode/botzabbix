import logging
from telegram import Update
from telegram.ext import ContextTypes
from zabbix import get_zabbix_api
from db import save_problem
from screenshot import send_alert_with_screenshot
from decorators import admin_only
from utils import retry, format_timestamp
from config import Config

logger = logging.getLogger(__name__)

class GetProblemsCommand:
    @admin_only
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        try:
            await update.message.reply_text("Đang lấy problems mới nhất...")
            
            zapi = get_zabbix_api()
            problems = self._fetch_problems(zapi)
            
            if not problems:
                await update.message.reply_text("Không có problems mới nào.")
                return
                
            await update.message.reply_text(f"Tìm thấy {len(problems)} problems mới nhất:")
            
            # Process each problem
            for problem in problems:
                await self._process_problem(problem, update.effective_chat.id, context)
                
        except Exception as e:
            logger.error(f"Error fetching latest problems: {str(e)}")
            await update.message.reply_text(f"Lỗi khi lấy problems: {str(e)}")
            return

    def _fetch_problems(self, zapi):
        """Fetch problems from Zabbix filtered by host groups"""
        # Get host group IDs if specified
        host_group_ids = []
        if Config.HOST_GROUPS:
            host_groups = zapi.hostgroup.get({
                "output": ["groupid", "name"],
                "filter": {"name": Config.HOST_GROUPS}
            })
            host_group_ids = [group["groupid"] for group in host_groups]
        
        # Get hosts from specified host groups
        host_ids = []
        if host_group_ids:
            hosts = zapi.host.get({
                "output": ["hostid"],
                "groupids": host_group_ids
            })
            host_ids = [host["hostid"] for host in hosts]
        
        # Build problem query
        problem_params = {
            "output": ["objectid", "name", "clock", "severity", "acknowledged"],
            "selectHosts": ["host"],
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": 10,
            "recent": True
        }
        
        # Add host filter if host groups are specified
        if host_ids:
            problem_params["hostids"] = host_ids
        
        problems = zapi.problem.get(problem_params)
        
        # Get trigger information for each problem
        if problems:
            trigger_ids = [problem["objectid"] for problem in problems]
            triggers = zapi.trigger.get({
                "output": ["description", "priority"],
                "triggerids": trigger_ids
            })
            
            # Create a mapping of trigger_id to trigger info
            trigger_map = {trigger["triggerid"]: trigger for trigger in triggers}
            
            # Enhance problems with trigger information
            for problem in problems:
                trigger_id = problem["objectid"]
                if trigger_id in trigger_map:
                    problem["trigger_description"] = trigger_map[trigger_id]["description"]
                    problem["priority"] = trigger_map[trigger_id]["priority"]
                else:
                    problem["trigger_description"] = problem["name"]
                    problem["priority"] = 0
        
        return problems

    async def _process_problem(self, problem, chat_id, context):
        """Process individual problem"""
        host = problem['hosts'][0]['host'] if problem['hosts'] else "Unknown"
        problem_info = {
            'problem_id': problem['objectid'],
            'host': host,
            'description': problem.get('trigger_description', problem['name']),
            'priority': problem.get('priority', 0),
            'timestamp': int(problem['clock']),
            'severity': problem['severity'],
            'acknowledged': problem['acknowledged']
        }
        
        # Save to database
        save_problem(
            problem_info['problem_id'],
            problem_info['host'],
            problem_info['description'],
            problem_info['priority'],
            problem_info['timestamp'],
            problem_info['severity']
        )
        
        # Send with screenshot
        await send_alert_with_screenshot(chat_id, problem_info, context)
