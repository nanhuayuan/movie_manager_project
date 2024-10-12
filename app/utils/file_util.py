import os

class FileUtil:
    @staticmethod
    def read_file(file_path):
        """读取文件内容并返回"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{file_path} not found.")
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    @staticmethod
    def write_file(file_path, content):
        """将内容写入文件"""
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)

    @staticmethod
    def read_lines(file_path):
        """读取文件中的每一行并返回列表"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{file_path} not found.")
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.readlines()
