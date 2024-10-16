# movie_schema.py
from marshmallow import Schema, fields
from .director_schema import DirectorSchema
from .genre_schema import GenreSchema
from .star_schema import StarSchema


class MovieSchema(Schema):
    """
    字段解释

    id = fields.Int(dump_only=True)     这是电影的唯一标识符。
    dump_only=True                      表示这个字段只用于序列化（输出），不用于反序列化（输入）。这通常用于数据库自动生成的 ID。
    title = fields.Str(required=True)   电影标题，使用字符串类型。
    required=True                       表示这是一个必填字段。在反序列化时，如果没有提供这个字段，会抛出验证错误。
    release_date = fields.Date()        电影的发布日期，使用 Date 类型。这个字段会自动处理日期的序列化和反序列化。
    description = fields.Str()          电影描述，使用字符串类型。这是一个可选字段，因为没有 required=True。
    director = fields.Nested(DirectorSchema)    这是一个嵌套字段，使用 DirectorSchema 来序列化和反序列化导演信息。
                                                允许我们在电影数据中包含完整的导演信息，而不仅仅是 ID。
    genres = fields.List(fields.Nested(GenreSchema))    这是一个列表字段，其中每个元素都是一个嵌套的 GenreSchema。
                                                        用于表示一部电影可能属于多个类型。
    stars = fields.List(fields.Nested(StarSchema))  类似于 genres，这是一个包含多个 StarSchema 的列表。
                                                    用于表示一部电影可能有多个主演。
    download_status = fields.Str()      表示电影的下载状态，使用字符串类型。
                                        可以用来标记如 "未下载"、"下载中"、"已下载" 等状态。
    local_path = fields.Str()   表示电影文件在本地的存储路径，使用字符串类型。

    序列化（将 Python 对象转换为 JSON）：
    movie_data = {
        'id': 1,
        'title': '超人',
        'release_date': '2023-07-01',
        'director': {'name': '张三'},
        'genres': [{'name': '动作'}, {'name': '科幻'}],
        'stars': [{'name': '李四'}, {'name': '王五'}],
        'download_status': '已下载',
        'local_path': '/movies/superman.mp4'
    }

    schema = MovieSchema()
    result = schema.dump(movie_data)
    # result 现在是一个可以转换为 JSON 的字典

    反序列化（将 JSON 数据转换为 Python 对象）：
    json_data = '{"title": "超人", "release_date": "2023-07-01", "director": {"name": "张三"}}'
    schema = MovieSchema()
    result = schema.loads(json_data)
    # result 现在是一个包含验证后的数据的字典

    """
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True)
    release_date = fields.Date()
    description = fields.Str()
    director = fields.Nested(DirectorSchema)
    genres = fields.List(fields.Nested(GenreSchema))
    stars = fields.List(fields.Nested(StarSchema))
    download_status = fields.Str()
    local_path = fields.Str()
