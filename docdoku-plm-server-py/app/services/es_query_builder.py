class EsQueryBuilder:
    def __init__(self):
        from app.services.indexer_manager import indexer_manager as im
        self.im = im

    def search_parts(self, ws: str, params: dict) -> list:
        idx = self.im._part_index_name(ws)
        must = []
        if params.get("q"):
            must.append({"multi_match": {"query": params["q"], "fields": ["partNumber^2", "partName", "description"]}})
        if params.get("number"):
            must.append({"match": {"partNumber": params["number"]}})
        if params.get("name"):
            must.append({"match": {"partName": params["name"]}})
        if params.get("version"):
            must.append({"term": {"version": params["version"]}})
        if params.get("author"):
            must.append({"term": {"authorLogin": params["author"]}})
        body = {"query": {"bool": {"must": must}}} if must else {"query": {"match_all": {}}}
        body["from"] = params.get("from", 0)
        body["size"] = params.get("size", 20)
        result = self.im.es.search(index=idx, body=body, _source=["partKey"])
        return [h["_source"]["partKey"] for h in result["hits"]["hits"]]

    def search_documents(self, ws: str, params: dict) -> list:
        idx = self.im._doc_index_name(ws)
        must = []
        if params.get("q"):
            must.append({"multi_match": {"query": params["q"], "fields": ["docMasterId^2", "title"]}})
        if params.get("id"):
            must.append({"match": {"docMasterId": params["id"]}})
        if params.get("title"):
            must.append({"match": {"title": params["title"]}})
        if params.get("version"):
            must.append({"term": {"version": params["version"]}})
        if params.get("author"):
            must.append({"term": {"authorLogin": params["author"]}})
        body = {"query": {"bool": {"must": must}}} if must else {"query": {"match_all": {}}}
        body["from"] = params.get("from", 0)
        body["size"] = params.get("size", 20)
        result = self.im.es.search(index=idx, body=body, _source=["docKey"])
        return [h["_source"]["docKey"] for h in result["hits"]["hits"]]


es_query_builder = EsQueryBuilder()
