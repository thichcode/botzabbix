import logging
import time
from telegram import Update
from telegram.ext import ContextTypes
from decorators import admin_only
from zabbix import get_zabbix_api

logger = logging.getLogger(__name__)

class AnalyzeCommand:
    @admin_only
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await update.message.reply_text("Đang phân tích history problems trong 3 ngày qua...")
            zapi = get_zabbix_api()
            end_time = int(time.time())
            start_time = end_time - 86400 * 3  # 3 days

            problems = zapi.problem.get({
                "output": ["objectid", "name", "clock", "severity", "acknowledged"],
                "selectHosts": ["host"],
                "time_from": start_time,
                "time_till": end_time,
                "sortfield": "clock",
                "sortorder": "DESC"
            })

            if not problems:
                await update.message.reply_text("Không có problems nào trong 3 ngày qua để phân tích.")
                return

            trigger_ids = [problem["objectid"] for problem in problems]
            triggers = zapi.trigger.get({
                "output": ["triggerid", "description", "priority", "dependencies"],
                "triggerids": trigger_ids
            })

            trigger_map = {trigger["triggerid"]: trigger for trigger in triggers}

            analysis_data = self._analyze_problems(problems, trigger_map)
            
            report = self._generate_report(analysis_data)
            
            await update.message.reply_text(report, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in analyze_and_predict: {str(e)}")
            await update.message.reply_text(f"Lỗi khi phân tích và dự đoán: {str(e)}")

    def _analyze_problems(self, problems, trigger_map):
        analysis = {
            'total_problems': len(problems),
            'host_problems': {},
            'severity_distribution': {},
            'problem_patterns': {},
            'critical_hosts': set(),
            'host_dependencies': {},
            'problem_clusters': []
        }

        for problem in problems:
            trigger_id = problem["objectid"]
            host = problem['hosts'][0]['host'] if problem['hosts'] else "Unknown"
            severity = int(problem['severity'])

            if host not in analysis['host_problems']:
                analysis['host_problems'][host] = {'count': 0, 'severities': []}
            analysis['host_problems'][host]['count'] += 1
            analysis['host_problems'][host]['severities'].append(severity)

            if severity not in analysis['severity_distribution']:
                analysis['severity_distribution'][severity] = 0
            analysis['severity_distribution'][severity] += 1

            if trigger_id in trigger_map:
                description = trigger_map[trigger_id].get('description', problem['name'])
                if description not in analysis['problem_patterns']:
                    analysis['problem_patterns'][description] = {'count': 0, 'hosts': set()}
                analysis['problem_patterns'][description]['count'] += 1
                analysis['problem_patterns'][description]['hosts'].add(host)

            if severity >= 4:
                analysis['critical_hosts'].add(host)

        analysis['host_dependencies'] = self._analyze_host_dependencies(problems, trigger_map)
        analysis['problem_clusters'] = self._find_problem_clusters(problems)

        return analysis

    def _analyze_host_dependencies(self, problems, trigger_map):
        dependencies = {}
        for problem in problems:
            trigger_id = problem["objectid"]
            host = problem['hosts'][0]['host'] if problem['hosts'] else "Unknown"
            if trigger_id in trigger_map:
                trigger_deps = trigger_map[trigger_id].get('dependencies', [])
                if trigger_deps:
                    if host not in dependencies:
                        dependencies[host] = {'depends_on': set(), 'depended_by': set()}
                    for dep_trigger_id in trigger_deps:
                        for other_problem in problems:
                            if other_problem["objectid"] == dep_trigger_id:
                                dep_host = other_problem['hosts'][0]['host'] if other_problem['hosts'] else "Unknown"
                                dependencies[host]['depends_on'].add(dep_host)
                                if dep_host not in dependencies:
                                    dependencies[dep_host] = {'depends_on': set(), 'depended_by': set()}
                                dependencies[dep_host]['depended_by'].add(host)
                                break
        return dependencies

    def _find_problem_clusters(self, problems):
        clusters = []
        sorted_problems = sorted(problems, key=lambda x: int(x['clock']))
        time_window = 300  # 5 minutes
        current_cluster = []
        for problem in sorted_problems:
            if not current_cluster or int(problem['clock']) - int(current_cluster[-1]['clock']) <= time_window:
                current_cluster.append(problem)
            else:
                if len(current_cluster) > 1:
                    clusters.append(current_cluster)
                current_cluster = [problem]
        if len(current_cluster) > 1:
            clusters.append(current_cluster)
        return clusters

    def _generate_report(self, analysis):
        report = "🔍 **BÁO CÁO PHÂN TÍCH PROBLEMS (3 NGÀY QUA)**\n\n"
        report += f"📊 **Tổng quan:**\n"
        report += f"- Tổng số problems: {analysis['total_problems']}\n"
        report += f"- Số host bị ảnh hưởng: {len(analysis['host_problems'])}\n"
        report += f"- Hosts critical (severity >= 4): {len(analysis['critical_hosts'])}\n\n"
        
        severity_names = {0: 'Not classified', 1: 'Information', 2: 'Warning', 3: 'Average', 4: 'High', 5: 'Disaster'}
        report += "🚨 **Phân bố mức độ nghiêm trọng:**\n"
        for severity, count in sorted(analysis['severity_distribution'].items()):
            report += f"- {severity_names.get(severity, f'Level {severity}')}: {count} problems\n"
        report += "\n"
        
        report += "🖥️ **Hosts có nhiều problems nhất:**\n"
        for host, data in sorted(analysis['host_problems'].items(), key=lambda x: x[1]['count'], reverse=True)[:5]:
            avg_severity = sum(data['severities']) / len(data['severities'])
            report += f"- {host}: {data['count']} problems (avg severity: {avg_severity:.1f})\n"
        report += "\n"
        
        report += "📋 **Patterns phổ biến:**\n"
        for pattern, data in sorted(analysis['problem_patterns'].items(), key=lambda x: x[1]['count'], reverse=True)[:3]:
            hosts_list = ', '.join(list(data['hosts'])[:3])
            if len(data['hosts']) > 3:
                hosts_list += f" và {len(data['hosts']) - 3} hosts khác"
            report += f"- {pattern}: {data['count']} lần (hosts: {hosts_list})\n"
        report += "\n"
        
        if analysis['critical_hosts']:
            report += "⚠️ **Hosts Critical cần chú ý:**\n"
            report += '\n'.join([f"- {host}" for host in analysis['critical_hosts']]) + "\n\n"
        
        if analysis['host_dependencies']:
            report += "🔗 **Mối quan hệ phụ thuộc:**\n"
            for host, deps in analysis['host_dependencies'].items():
                if deps['depends_on']:
                    report += f"- {host} phụ thuộc vào: {', '.join(deps['depends_on'])}\n"
                if deps['depended_by']:
                    report += f"- {host} ảnh hưởng đến: {', '.join(deps['depended_by'])}\n"
            report += "\n"
        
        if analysis['problem_clusters']:
            report += "⚡ **Clusters problems (xảy ra cùng lúc):**\n"
            for i, cluster in enumerate(analysis['problem_clusters'][:3], 1):
                hosts_in_cluster = {p['hosts'][0]['host'] for p in cluster if p['hosts']}
                report += f"- Cluster {i}: {len(cluster)} problems trên {len(hosts_in_cluster)} hosts ({', '.join(hosts_in_cluster)})\n"
            report += "\n"
        
        report += "🔮 **DỰ ĐOÁN VÀ KHUYẾN NGHỊ:**\n"
        sorted_patterns = sorted(analysis['problem_patterns'].items(), key=lambda x: x[1]['count'], reverse=True)
        if sorted_patterns:
            report += f"- Pattern '{sorted_patterns[0][0]}' có khả năng cao sẽ xảy ra lại\n"
        
        sorted_hosts = sorted(analysis['host_problems'].items(), key=lambda x: x[1]['count'], reverse=True)
        if sorted_hosts:
            report += f"- Host '{sorted_hosts[0][0]}' có nguy cơ cao gặp vấn đề tiếp theo\n"
        
        critical_dependencies = [(h, d['depended_by']) for h, d in analysis['host_dependencies'].items() if d['depended_by'] and h in analysis['critical_hosts']]
        if critical_dependencies:
            report += "- Các host critical có thể ảnh hưởng đến nhiều host khác:\n"
            for host, affected in critical_dependencies[:3]:
                report += f"  + {host} → {', '.join(list(affected)[:3])}\n"
        
        report += "\n💡 **KHUYẾN NGHỊ:**\n"
        if analysis['critical_hosts']:
            report += "- Ưu tiên kiểm tra và khắc phục các hosts critical\n"
        if analysis['problem_clusters']:
            report += "- Có thể có vấn đề chung gây ra nhiều problems cùng lúc\n"
        if analysis['host_dependencies']:
            report += "- Kiểm tra mối quan hệ phụ thuộc giữa các hosts\n"
        
        return report
