
from app.utils.magnet_util import MagnetUtil


def test_magnet_util():
    # 使用示例
    magnet_helper = MagnetUtil()

    # 从不同格式提取哈希值
    hash1 = magnet_helper.extract_hash("cfd6b190df47342a17415cb4c930db90968c0342")
    hash2 = magnet_helper.extract_hash("magnet:?xt=urn:btih:cfd6b190df47342a17415cb4c930db90968c0342")

    # 生成有效的磁力链接
    magnet1 = magnet_helper.generate_valid_magnet("cfd6b190df47342a17415cb4c930db90968c0342")
    magnet2 = magnet_helper.generate_valid_magnet(
        "magnet:?xt=urn:btih:cfd6b190df47342a17415cb4c930db90968c0342&dn=测试文件")

    # 简化磁力链接
    simple_magnet = magnet_helper.simplify_magnet_link(
        "magnet:?xt=urn:btih:cfd6b190df47342a17415cb4c930db90968c0342&dn=测试文件&tr=http://tracker.example.com")

    print(f"提取的哈希值1: {hash1}")
    print(f"提取的哈希值2: {hash2}")
    print(f"生成的磁力链接1: {magnet1}")
    print(f"生成的磁力链接2: {magnet2}")
    print(f"简化后的磁力链接: {simple_magnet}")


