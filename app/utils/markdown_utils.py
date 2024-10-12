import markdown

def parse_markdown(file_path):
    """解析 Markdown 文件并返回 HTML 内容"""
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()
    return markdown.markdown(text)

def extract_movie_ids(markdown_content):
    """从 Markdown 中提取电影编号"""
    # 假设电影编号按特定格式存储，如 `[Movie ID]`
    import re
    return re.findall(r'\[(.*?)\]', markdown_content)
