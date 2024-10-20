class ModelConverter:
    @staticmethod
    def dict_to_model(data: dict, model_class):
        """将字典转换为模型实例"""
        if not data:
            return None

        instance = model_class()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance
