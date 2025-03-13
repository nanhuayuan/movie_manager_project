import re
import base64
import urllib.parse
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


class MagnetUtil:
    def extract_hash(self, input_string: str) -> str:
        """
        从输入字符串中提取BitTorrent hash值

        参数:
        input_string (str): 磁力链接或纯哈希值

        返回:
        str: 提取出的哈希值，如果未找到则返回空字符串

        异常:
        ValueError: 当输入的格式无效时抛出
        """
        # 处理纯哈希输入（40位十六进制或32位Base32）
        if re.match(r'^[a-fA-F0-9]{40}$', input_string):
            return input_string.lower()
        elif re.match(r'^[A-Z2-7]{32}$', input_string.upper()):
            return self.base32_to_hex(base32_hash=input_string.upper())

        # 检查是否是磁力链接
        elif input_string.startswith('magnet:'):
            # 尝试找到 btih 参数
            hash_match = re.search(r'btih:([a-zA-Z0-9]{40}|[A-Z2-7]{32})', input_string, re.IGNORECASE)
            if hash_match:
                hash_value = hash_match.group(1)
                if len(hash_value) == 32 and re.match(r'^[A-Z2-7]{32}$', hash_value.upper()):
                    return self.base32_to_hex(base32_hash=hash_value.upper())
                return hash_value.lower()

            # 尝试从URL参数中提取
            parsed = urlparse(input_string)
            params = parse_qs(parsed.query)

            for key in params:
                if key.lower() == 'xt' or key.lower() == 'xt.1':
                    for value in params[key]:
                        if 'btih:' in value.lower():
                            hash_value = value.split('btih:')[-1].split('&')[0]
                            # 检查是否为Base32格式
                            if len(hash_value) == 32 and re.match(r'^[A-Z2-7]{32}$', hash_value.upper()):
                                return self.base32_to_hex(base32_hash=hash_value.upper())
                            return hash_value.lower()

        raise ValueError("Invalid hash or magnet link format")

    def base32_to_hex(self, base32_hash: str) -> str:
        """
        将 Base32 编码的哈希值转换为十六进制（小写）

        参数:
            base32_hash (str): 32位Base32编码字符串（仅含字母A-Z和数字2-7）

        返回:
            str: 40位十六进制哈希值（小写）

        异常:
            ValueError: 输入不符合Base32规范或解码后长度错误
        """
        # 校验输入格式
        if not re.match(r'^[A-Z2-7]{32}$', base32_hash.upper()):
            raise ValueError("Invalid Base32 hash format")

        try:
            # 补足Base32填充符"="（若需要）
            padded_hash = base32_hash.upper() + '=' * ((8 - len(base32_hash) % 8) % 8)
            # 解码为字节
            decoded_bytes = base64.b32decode(padded_hash)
            # 校验解码后的字节长度（SHA1应为20字节）
            if len(decoded_bytes) != 20:
                raise ValueError("Decoded hash length is not 20 bytes")
            # 转为十六进制字符串（小写）
            return decoded_bytes.hex().lower()
        except (base64.binascii.Error, TypeError) as e:
            raise ValueError(f"Base32 decoding failed: {e}")

    def generate_valid_magnet(self, input_string: str) -> str:
        """
        生成有效的磁力链接

        参数:
        input_string (str): 磁力链接或纯哈希值

        返回:
        str: 有效的磁力链接，如果输入无效则返回空字符串
        """
        try:
            hash_value = self.extract_hash(input_string)
        except ValueError:
            return ""

        # 构建基本的磁力链接参数
        magnet_params = {
            'xt': [f'urn:btih:{hash_value}']
        }

        # 如果原始输入是磁力链接，尝试保留其他有用的参数
        if input_string.startswith('magnet:'):
            parsed = urlparse(input_string)
            params = parse_qs(parsed.query)

            # 保留显示名称
            if 'dn' in params:
                magnet_params['dn'] = params['dn']

            # 保留tracker
            if 'tr' in params:
                magnet_params['tr'] = params['tr']

        # 如果没有tracker，添加一些公共tracker
        if 'tr' not in magnet_params:
            magnet_params['tr'] = [
                'udp://tracker.opentrackr.org:1337/announce',
                'udp://open.tracker.cl:1337/announce',
                'udp://tracker.openbittorrent.com:6969/announce'
            ]

        # 构建最终的磁力链接
        query_string = urlencode(magnet_params, doseq=True)
        return f"magnet:?{query_string}"

    def simplify_magnet_link(self, magnet_link: str) -> str:
        """
        简化磁力链接，只保留必要的部分以确保可下载
        移除冗余参数（如dn），保留xt和tr，确保链接简洁有效

        参数:
        magnet_link (str): 原始磁力链接

        返回:
        str: 简化后的磁力链接，如果输入无效则返回None
        """
        if not magnet_link.startswith('magnet:?'):
            return None

        parsed = urlparse(magnet_link)
        query_params = parse_qs(parsed.query)

        # 保留必要参数（xt和tr）
        required_params = {}

        # 添加xt参数（必需）
        if 'xt' in query_params:
            required_params['xt'] = query_params['xt']
        else:
            return None  # 没有xt参数的磁力链接无效

        # 添加tr参数（如果有）
        if 'tr' in query_params:
            # 最多保留5个tracker以保持链接简洁
            required_params['tr'] = query_params['tr'][:5]

        # 重构磁力链接
        new_query = urlencode(required_params, doseq=True)
        return f"magnet:?{new_query}"