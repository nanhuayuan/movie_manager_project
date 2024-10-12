# magnet_schema.py
from marshmallow import Schema, fields

class MagnetSchema(Schema):
    id = fields.Int(dump_only=True)
    movie_id = fields.Int(required=True)
    magnet_link = fields.Str(required=True)
    seeds = fields.Int()
    peers = fields.Int()
    size = fields.Str()
    upload_date = fields.DateTime()