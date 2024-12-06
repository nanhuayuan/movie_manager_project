import pandas as pd
import re


def extract_value(text, key):
    # 通用提取模式
    pattern = f'{key}:"([^"]*)"'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None


def process_log_data(text):
    data = []
    current_source = None

    for line in text.split('\n'):
        line = line.strip()

        # 跳过空行
        if not line:
            continue

        # 检查是否是来源行（ng1, 2, 3等）
        if re.match(r'^[a-zA-Z0-9]+$', line):
            current_source = line
            continue

        # 处理日志行
        if line.startswith('http_host'):
            row_data = {'source': current_source}

            # 提取所有字段
            fields = ['http_host', 'remote_addr', 'remote_port', 'remote_user',
                      'time', 'request', 'code', 'body', 'http_referer',
                      'ar_time', 'RealIp', 'agent']

            for field in fields:
                value = extract_value(line, field)
                if value:
                    # 特殊处理time字段
                    if field == 'time':
                        value = value.replace('+08:00', '')
                    row_data[field] = value

            data.append(row_data)

    return pd.DataFrame(data)


# 读取文本文件
with open('30日.txt', 'r', encoding='utf-8') as file:
    log_text = file.read()

# 处理数据
df = process_log_data(log_text)

# 保存到Excel
df.to_excel('log_analysis.xlsx', index=False)

# 打印数据框的前几行以验证结果
print(df.head())