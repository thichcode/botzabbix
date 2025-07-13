import os
import logging
import time
from telegram import Update
from telegram.ext import ContextTypes
from zabbix import get_zabbix_api
from decorators import admin_only

logger = logging.getLogger(__name__)

class AnalyzeCommand:
    @admin_only
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await update.message.reply_text("Đang phân tích history problems trong 3 ngày qua...")
            zapi = get_zabbix_api()
            end_time = int(time.time())
            start_time = end_time - 86400 * 3  # 3 days

            # Lấy problems trong 3 ngày qua
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

            # Lấy thông tin trigger cho mỗi problem
            trigger_ids = [problem["objectid"] for problem in problems]
            triggers = zapi.trigger.get({
                "output": ["triggerid", "description", "priority", "dependencies"],
                "triggerids": trigger_ids
            })

            # Tạo mapping trigger_id -> trigger
            trigger_map = {trigger["triggerid"]: trigger for trigger in triggers}

            # Phân tích dữ liệu
            analysis_data = self._analyze_problems(problems, trigger_map)
            
            # Tạo báo cáo
            report = self._generate_report(analysis_data)
            
            await update.message.reply_text(report)
            
        except Exception as e:
            logger.error(f"Error in analyze_and_predict: {str(e)}")
            await update.message.reply_text(f"Lỗi khi phân tích và dự đoán: {str(e)}")

    def _analyze_problems(self, problems, trigger_map):
        """Phân tích problems và tìm mối quan hệ"""
        analysis = {
            'total_problems': len(problems),
            'host_problems': {},
            'severity_distribution': {},
            'time_distribution': {},
            'problem_patterns': {},
            'host_dependencies': {},
            'critical_hosts': set(),
            'problem_clusters': []
        }

        # Phân tích từng problem
        for problem in problems:
            trigger_id = problem["objectid"]
            host = problem['hosts'][0]['host'] if problem['hosts'] else "Unknown"
            severity = int(problem['severity'])
            timestamp = int(problem['clock'])
            day = time.strftime('%Y-%m-%d', time.localtime(timestamp))
            hour = time.strftime('%H', time.localtime(timestamp))

            # Thống kê theo host
            if host not in analysis['host_problems']:
                analysis['host_problems'][host] = {
                    'count': 0,
                    'severities': [],
                    'problems': [],
                    'last_problem': None
                }
            
            analysis['host_problems'][host]['count'] += 1
            analysis['host_problems'][host]['severities'].append(severity)
            analysis['host_problems'][host]['problems'].append(problem)
            
            if not analysis['host_problems'][host]['last_problem'] or timestamp > int(analysis['host_problems'][host]['last_problem']['clock']):
                analysis['host_problems'][host]['last_problem'] = problem

            # Thống kê theo severity
            if severity not in analysis['severity_distribution']:
                analysis['severity_distribution'][severity] = 0
            analysis['severity_distribution'][severity] += 1

            # Thống kê theo thời gian
            if day not in analysis['time_distribution']:
                analysis['time_distribution'][day] = {'total': 0, 'hours': {}}
            analysis['time_distribution'][day]['total'] += 1
            
            if hour not in analysis['time_distribution'][day]['hours']:
                analysis['time_distribution'][day]['hours'][hour] = 0
            analysis['time_distribution'][day]['hours'][hour] += 1

            # Phân tích pattern
            if trigger_id in trigger_map:
                trigger = trigger_map[trigger_id]
                description = trigger.get('description', problem['name'])
                
                if description not in analysis['problem_patterns']:
                    analysis['problem_patterns'][description] = {
                        'count': 0,
                        'hosts': set(),
                        'severities': []
                    }
                
                analysis['problem_patterns'][description]['count'] += 1
                analysis['problem_patterns'][description]['hosts'].add(host)
                analysis['problem_patterns'][description]['severities'].append(severity)

            # Xác định critical hosts (severity >= 4)
            if severity >= 4:
                analysis['critical_hosts'].add(host)

        # Phân tích mối quan hệ giữa các host
        analysis['host_dependencies'] = self._analyze_host_dependencies(problems, trigger_map)
        
        # Tìm clusters của problems
        analysis['problem_clusters'] = self._find_problem_clusters(problems, trigger_map)

        return analysis

    def _analyze_host_dependencies(self, problems, trigger_map):
        """Phân tích mối quan hệ phụ thuộc giữa các host"""
        dependencies = {}
        
        for problem in problems:
            trigger_id = problem["objectid"]
            host = problem['hosts'][0]['host'] if problem['hosts'] else "Unknown"
            
            if trigger_id in trigger_map:
                trigger = trigger_map[trigger_id]
                trigger_deps = trigger.get('dependencies', [])
                
                if trigger_deps:
                    if host not in dependencies:
                        dependencies[host] = {'depends_on': set(), 'depended_by': set()}
                    
                    # Host này phụ thuộc vào các trigger khác
                    for dep_trigger_id in trigger_deps:
                        # Tìm host của trigger dependency
                        for other_problem in problems:
                            if other_problem["objectid"] == dep_trigger_id:
                                dep_host = other_problem['hosts'][0]['host'] if other_problem['hosts'] else "Unknown"
                                dependencies[host]['depends_on'].add(dep_host)
                                
                                if dep_host not in dependencies:
                                    dependencies[dep_host] = {'depends_on': set(), 'depended_by': set()}
                                dependencies[dep_host]['depended_by'].add(host)
                                break

        return dependencies

    def _find_problem_clusters(self, problems, trigger_map):
        """Tìm các cluster của problems xảy ra cùng thời gian"""
        clusters = []
        time_window = 300  # 5 phút
        
        # Sắp xếp problems theo thời gian
        sorted_problems = sorted(problems, key=lambda x: int(x['clock']))
        
        current_cluster = []
        for problem in sorted_problems:
            if not current_cluster:
                current_cluster = [problem]
            else:
                # Kiểm tra xem problem này có thuộc cluster hiện tại không
                last_problem_time = int(current_cluster[-1]['clock'])
                current_problem_time = int(problem['clock'])
                
                if current_problem_time - last_problem_time <= time_window:
                    current_cluster.append(problem)
                else:
                    # Kết thúc cluster hiện tại
                    if len(current_cluster) > 1:
                        clusters.append(current_cluster)
                    current_cluster = [problem]
        
        # Thêm cluster cuối cùng
        if len(current_cluster) > 1:
            clusters.append(current_cluster)
        
        return clusters

    def _generate_report(self, analysis):
        """Tạo báo cáo phân tích"""
        report = "🔍 **BÁO CÁO PHÂN TÍCH PROBLEMS (3 NGÀY QUA)**\n\n"
        
        # Tổng quan
        report += f"📊 **Tổng quan:**\n"
        report += f"- Tổng số problems: {analysis['total_problems']}\n"
        report += f"- Số host bị ảnh hưởng: {len(analysis['host_problems'])}\n"
        report += f"- Hosts critical (severity >= 4): {len(analysis['critical_hosts'])}\n\n"
        
        # Phân bố severity
        report += "🚨 **Phân bố mức độ nghiêm trọng:**\n"
        severity_names = {0: 'Not classified', 1: 'Information', 2: 'Warning', 3: 'Average', 4: 'High', 5: 'Disaster'}
        for severity, count in sorted(analysis['severity_distribution'].items()):
            severity_name = severity_names.get(severity, f'Level {severity}')
            report += f"- {severity_name}: {count} problems\n"
        report += "\n"
        
        # Hosts có nhiều problems nhất
        report += "🖥️ **Hosts có nhiều problems nhất:**\n"
        sorted_hosts = sorted(analysis['host_problems'].items(), key=lambda x: x[1]['count'], reverse=True)[:5]
        for host, data in sorted_hosts:
            avg_severity = sum(data['severities']) / len(data['severities'])
            report += f"- {host}: {data['count']} problems (avg severity: {avg_severity:.1f})\n"
        report += "\n"
        
        # Patterns phổ biến
        report += "📋 **Patterns phổ biến:**\n"
        sorted_patterns = sorted(analysis['problem_patterns'].items(), key=lambda x: x[1]['count'], reverse=True)[:3]
        for pattern, data in sorted_patterns:
            hosts_list = ', '.join(list(data['hosts'])[:3])
            if len(data['hosts']) > 3:
                hosts_list += f" và {len(data['hosts']) - 3} hosts khác"
            report += f"- {pattern}: {data['count']} lần (hosts: {hosts_list})\n"
        report += "\n"
        
        # Critical hosts
        if analysis['critical_hosts']:
            report += "⚠️ **Hosts Critical cần chú ý:**\n"
            for host in analysis['critical_hosts']:
                report += f"- {host}\n"
            report += "\n"
        
        # Mối quan hệ phụ thuộc
        if analysis['host_dependencies']:
            report += "🔗 **Mối quan hệ phụ thuộc:**\n"
            for host, deps in analysis['host_dependencies'].items():
                if deps['depends_on']:
                    depends_on = ', '.join(deps['depends_on'])
                    report += f"- {host} phụ thuộc vào: {depends_on}\n"
                if deps['depended_by']:
                    depended_by = ', '.join(deps['depended_by'])
                    report += f"- {host} ảnh hưởng đến: {depended_by}\n"
            report += "\n"
        
        # Problem clusters
        if analysis['problem_clusters']:
            report += "⚡ **Clusters problems (xảy ra cùng lúc):**\n"
            for i, cluster in enumerate(analysis['problem_clusters'][:3], 1):
                hosts_in_cluster = set()
                for problem in cluster:
                    host = problem['hosts'][0]['host'] if problem['hosts'] else "Unknown"
                    hosts_in_cluster.add(host)
                hosts_str = ', '.join(hosts_in_cluster)
                report += f"- Cluster {i}: {len(cluster)} problems trên {len(hosts_in_cluster)} hosts ({hosts_str})\n"
            report += "\n"
        
        # Dự đoán
        report += "🔮 **DỰ ĐOÁN VÀ KHUYẾN NGHỊ:**\n"
        
        # Dự đoán dựa trên patterns
        if sorted_patterns:
            most_frequent_pattern = sorted_patterns[0]
            report += f"- Pattern '{most_frequent_pattern[0]}' có khả năng cao sẽ xảy ra lại\n"
        
        # Dự đoán dựa trên hosts
        if sorted_hosts:
            most_affected_host = sorted_hosts[0]
            report += f"- Host '{most_affected_host[0]}' có nguy cơ cao gặp vấn đề tiếp theo\n"
        
        # Dự đoán dựa trên dependencies
        critical_dependencies = []
        for host, deps in analysis['host_dependencies'].items():
            if deps['depended_by'] and host in analysis['critical_hosts']:
                critical_dependencies.append((host, deps['depended_by']))
        
        if critical_dependencies:
            report += "- Các host critical có thể ảnh hưởng đến nhiều host khác:\n"
            for host, affected_hosts in critical_dependencies[:3]:
                affected_list = ', '.join(list(affected_hosts)[:3])
                report += f"  + {host} → {affected_list}\n"
        
        # Khuyến nghị
        report += "\n💡 **KHUYẾN NGHỊ:**\n"
        if analysis['critical_hosts']:
            report += "- Ưu tiên kiểm tra và khắc phục các hosts critical\n"
        if analysis['problem_clusters']:
            report += "- Có thể có vấn đề chung gây ra nhiều problems cùng lúc\n"
        if analysis['host_dependencies']:
            report += "- Kiểm tra mối quan hệ phụ thuộc giữa các hosts\n"
        report += "- Tăng cường monitoring cho các hosts có nhiều problems\n"
        report += "- Xem xét cập nhật cấu hình hoặc thay thế thiết bị có vấn đề\n"
        
        return report
