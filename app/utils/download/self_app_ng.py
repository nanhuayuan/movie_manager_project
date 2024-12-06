import re
import pandas as pd
from datetime import datetime
import argparse
import sys
from typing import List, Dict


class NgLogParser:
    def __init__(self):
        # 定义日志解析的正则表达式
        self.log_pattern = r'(?P<remote_addr>[\d\.]+) - - \[(?P<time>[^\]]+)\]\[(?P<duration>[\d\.]+)\] "(?P<method>\w+) (?P<api>[^ ]*) (?P<protocol>[^"]*)" (?P<code>\d+) (?P<size>\d+) "[^"]*" "(?P<source>[^"]*)" "(?P<source_ip>[^"]*)".*?"timestamp": "(?P<timestamp>\d+)".*?"version": "(?P<version>[^"]*)".*?"appKey": "(?P<appKey>[^"]*)".*?"zgtSign": "(?P<zgtSign>[^"]*)"'
        self.pattern = re.compile(self.log_pattern)

    def parse_time(self, time_str: str) -> str:
        """将日志中的时间字符串转换为指定格式"""
        dt = datetime.strptime(time_str, "%d/%b/%Y:%H:%M:%S +0800")
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def timestamp_to_time(self, timestamp: str) -> str:
        """将时间戳转换为东八区时间字符串"""
        dt = datetime.fromtimestamp(int(timestamp) / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def parse_log_line(self, line: str) -> Dict:
        """解析单行日志"""
        match = self.pattern.match(line)
        if not match:
            return None

        data = match.groupdict()
        # 转换时间格式
        data['time'] = self.parse_time(data['time'])
        data['timestamp_formatted'] = self.timestamp_to_time(data['timestamp'])
        return data

    def parse_log_file(self, input_file: str) -> List[Dict]:
        """解析整个日志文件"""
        parsed_logs = []
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                parsed_line = self.parse_log_line(line.strip())
                if parsed_line:
                    parsed_logs.append(parsed_line)
        return parsed_logs

    def save_to_excel(self, parsed_logs: List[Dict], output_file: str):
        """将解析结果保存为Excel文件"""
        df = pd.DataFrame(parsed_logs)
        # 重新排列列顺序
        columns = ['remote_addr', 'time', 'duration', 'method', 'api', 'protocol',
                   'code', 'size', 'source', 'source_ip', 'timestamp',
                   'timestamp_formatted', 'version', 'appKey', 'zgtSign']
        df = df[columns]
        df.to_excel(output_file, index=False)


def parse_and_save(input_file: str, output_file: str):
    """便捷函数用于直接调用"""
    parser = NgLogParser()
    logs = parser.parse_log_file(input_file)
    parser.save_to_excel(logs, output_file)


def main():
    """主函数，支持直接运行"""
    parser = argparse.ArgumentParser(description='Parse Nginx logs to Excel')
    parser.add_argument('-i', '--input', default='zd-11-01-样例.txt',
                        help='Input log file path (default: zd-11-01-样例.txt)')
    parser.add_argument('-o', '--output', default='nginx_logs.xlsx',
                        help='Output Excel file path (default: nginx_logs.xlsx)')

    if len(sys.argv) > 1:
        args = parser.parse_args()
        input_file = args.input
        output_file = args.output
    else:
        file_name = 'zd-11-01'
        input_file = f'{file_name}.txt'
        output_file = f'{file_name}.xlsx'
        #input_file = 'zd-11-01-样例.txt'
        #output_file = 'nginx_logs.xlsx'

    parse_and_save(input_file, output_file)
    print(f"Log parsing completed. Results saved to {output_file}")


if __name__ == "__main__":
    main()