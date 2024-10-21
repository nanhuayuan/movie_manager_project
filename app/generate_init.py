import os


def generate_init():
    services_dir = 'app/services'  # 服务目录
    init_file = os.path.join(services_dir, '__init__.py')

    # 获取所有.py文件
    py_files = [f for f in os.listdir(services_dir) if f.endswith('.py') and f != '__init__.py']

    with open(init_file, 'w') as f:
        # 导入所有服务类
        for py_file in py_files:
            class_name = py_file[:-3].capitalize() + "Service"  # 假设类名是文件名的大写形式
            f.write(f"from .{py_file[:-3]} import {class_name}\n")

        # 添加__all__定义
        f.write("\n__all__ = [\n")
        for py_file in py_files:
            class_name = py_file[:-3].capitalize() + "Service"
            f.write(f"    '{class_name}',\n")
        f.write("]\n")


if __name__ == '__main__':
    generate_init()
