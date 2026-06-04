from rest_framework.renderers import JSONRenderer
from rest_framework.utils.encoders import JSONEncoder


class MongoJSONEncoder(JSONEncoder):
    def default(self, obj):
        # Handle bson ObjectId safely
        if obj.__class__.__name__ == "ObjectId":
            return str(obj)
        try:
            from bson import ObjectId

            if isinstance(obj, ObjectId):
                return str(obj)
        except ImportError:
            pass
        return super().default(obj)


class CustomJSONRenderer(JSONRenderer):
    encoder_class = MongoJSONEncoder
