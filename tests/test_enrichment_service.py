import pandas as pd

from logic.services import enrichment_service


class _FakeDoc:
    def __init__(self, exists=False, data=None):
        self.exists = exists
        self._data = data or {}

    def to_dict(self):
        return self._data


class _FakeDocRef:
    def __init__(self, doc):
        self._doc = doc
        self.set_called = False

    def get(self):
        return self._doc

    def set(self, *_args, **_kwargs):
        self.set_called = True


class _FakeCollection:
    def __init__(self, doc_ref):
        self._doc_ref = doc_ref

    def document(self, _name):
        return self._doc_ref


class _FakeDb:
    def __init__(self, doc_ref):
        self._doc_ref = doc_ref

    def collection(self, _name):
        return _FakeCollection(self._doc_ref)


class _FakeAdapter:
    def __init__(self, db):
        self._db = db

    def _get_db(self):
        return self._db


def test_load_mapping_nao_cria_perfil_quando_nao_existe(monkeypatch):
    doc_ref = _FakeDocRef(_FakeDoc(exists=False))
    fake_db = _FakeDb(doc_ref)
    fake_adapter = _FakeAdapter(fake_db)

    monkeypatch.setattr(enrichment_service, "_get_adapter", lambda: fake_adapter)
    monkeypatch.setattr(enrichment_service, "_load_local_legacy", lambda _name: None)

    result = enrichment_service.load_mapping("Perfil_Inexistente")

    assert result is None
    assert doc_ref.set_called is False


def test_load_mapping_retorna_dataframe_quando_existe(monkeypatch):
    payload = {"UC001": {"Razao Social": "Cliente A"}}
    doc_ref = _FakeDocRef(_FakeDoc(exists=True, data=payload))
    fake_db = _FakeDb(doc_ref)
    fake_adapter = _FakeAdapter(fake_db)

    monkeypatch.setattr(enrichment_service, "_get_adapter", lambda: fake_adapter)
    monkeypatch.setattr(enrichment_service, "_load_local_legacy", lambda _name: None)

    result = enrichment_service.load_mapping("Perfil_Existente")

    assert isinstance(result, pd.DataFrame)
    assert "No. UC" in result.columns
    assert len(result) == 1
