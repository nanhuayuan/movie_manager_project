import os
import re

def extract_classes_from_file(input_file, output_dir):
    with open(input_file, 'r', encoding="utf-8") as file:
        content = file.read()

    # 使用正则表达式匹配所有类的定义
    class_pattern = r"(class\s+\w+\(.*?\):\s+(?:[ \t].*?\n)+)"
    classes = re.findall(class_pattern, content, re.DOTALL)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 提取每个类，并写入单独的文件中
    for class_content in classes:
        class_name = re.search(r"class\s+(\w+)", class_content).group(1)
        output_file = os.path.join(output_dir, f"{class_name.lower()}.py")

        with open(output_file, 'w', encoding="utf-8") as class_file:
            class_file.write(class_content)

        print(f"类 {class_name} 已提取到 {output_file}")

if __name__ == "__main__":
    input_file = "movie_model.py"  # 原始models文件路径
    output_dir = "models"  # 目标文件夹
    extract_classes_from_file(input_file, output_dir)
