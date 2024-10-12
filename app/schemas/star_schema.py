# star_schema.py
from marshmallow import Schema, fields

class StarSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    birth_date = fields.Date()