from pathlib import Path
from typing import Dict, List, Optional, Protocol
import logging

from app.model.db.movie_model import ChartEntry
from app.model.db.movie_model import Chart

# 配置日志记录器
from app.utils.read_markdown_file.markdown_reader import MarkdownReader

logger = logging.getLogger(__name__)


class NormalMarkdownReader(MarkdownReader):
    """普通榜单 Markdown 读取器"""

    def process_file(self, file_path: Path = None) -> Optional[Chart]:
        """
        处理普通榜单文件

        Args:
            file_path: 文件路径

        Returns:
            Optional[Chart]: 处理后的 md_file 对象，失败返回 None
        """

        # 检查缓存
        cached_result = self._get_cached_result(file_path)
        if cached_result:
            return cached_result

        try:
            chart_obj = Chart()
            chart_obj.name = file_path.name.split('.')[0]
            chart_obj.file_path = str(file_path)
            chart_obj.entries = []

            with file_path.open('r', encoding='utf-8') as f:
                for line_number, line in enumerate(f, start=1):  # 使用enumerate并从1开始
                    chart_entry = ChartEntry()
                    chart_entry.serial_number = line.replace("<br>\n", "").strip()
                    if chart_entry.serial_number:  # 只添加非空行
                        chart_entry.rank = line_number  # 添加rank属性，从1开始
                        chart_obj.entries.append(chart_entry)

            # 缓存结果
            self._cache_result(file_path, chart_obj)
            return chart_obj
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时发生错误: {e}")
            return None
