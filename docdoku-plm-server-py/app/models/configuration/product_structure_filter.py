"""ProductStructureFilter 抽象基类 DTO。"""
class ProductStructureFilter:
    def filter(self, links: list) -> list:
        raise NotImplementedError
