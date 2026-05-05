from __future__ import annotations

from types import SimpleNamespace

import pytest

from libs.attio import sdk_boundary


class _FakeSDK:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class _FakePostRecordRequest:
    def __init__(self, *, values) -> None:
        self.values = values


class _FakePatchRecordRequest:
    def __init__(self, *, values) -> None:
        self.values = values


class _FakePostNoteRequest:
    def __init__(
        self,
        *,
        parent_object: str,
        parent_record_id: str,
        title: str,
        format_: str,
        content: str,
    ) -> None:
        self.parent_object = parent_object
        self.parent_record_id = parent_record_id
        self.title = title
        self.format_ = format_
        self.content = content


class _ErrWithBody(Exception):
    def __init__(self, body: object) -> None:
        super().__init__("boom")
        self.body = body


def test_get_attio_sdk_client_class_runtime_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sdk_boundary,
        "_import_attio_sdk_module",
        lambda: SimpleNamespace(SDK=_FakeSDK),
    )

    klass = sdk_boundary.get_attio_sdk_client_class()

    assert klass is _FakeSDK


def test_request_builders_use_runtime_model_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_models = SimpleNamespace(
        PostV2ObjectsObjectRecordsDataRequest=_FakePostRecordRequest,
        PatchV2ObjectsObjectRecordsRecordIDDataRequest=_FakePatchRecordRequest,
        PostV2NotesData=_FakePostNoteRequest,
    )
    monkeypatch.setattr(
        sdk_boundary,
        "_import_attio_models_module",
        lambda: fake_models,
    )

    post = sdk_boundary.build_post_record_request({"x": 1})
    patch = sdk_boundary.build_patch_record_request({"y": 2})
    note = sdk_boundary.build_post_note_request(
        parent_object="people",
        parent_record_id="rec_1",
        title="hi",
        format_="plaintext",
        content="hello",
    )

    assert isinstance(post, _FakePostRecordRequest)
    assert post.values == {"x": 1}
    assert isinstance(patch, _FakePatchRecordRequest)
    assert patch.values == {"y": 2}
    assert isinstance(note, _FakePostNoteRequest)
    assert note.parent_record_id == "rec_1"


def test_extract_exception_body_text_handles_text_bytes_and_object() -> None:
    assert sdk_boundary.extract_exception_body_text(_ErrWithBody("abc")) == "abc"
    assert sdk_boundary.extract_exception_body_text(_ErrWithBody(b"abc")) == "abc"
    assert (
        sdk_boundary.extract_exception_body_text(_ErrWithBody({"a": 1})) == "{'a': 1}"
    )
    assert sdk_boundary.extract_exception_body_text(Exception("fallback")) == "fallback"


def test_uniqueness_conflict_detection_uses_body_text() -> None:
    err = _ErrWithBody('{"type": "uniqueness_conflict"}')
    assert sdk_boundary.is_uniqueness_conflict(err) is True


def test_extract_existing_record_id_from_json_body() -> None:
    body = '{"data": {"existing_record": {"id": {"record_id": "rec_existing"}}}}'
    err = _ErrWithBody(body)

    assert sdk_boundary.extract_existing_record_id(err) == "rec_existing"


def test_model_dump_or_empty_uses_model_dump_if_available() -> None:
    class _ModelLike:
        def model_dump(self):
            return {"ok": True}

    assert sdk_boundary.model_dump_or_empty(_ModelLike()) == {"ok": True}
    assert sdk_boundary.model_dump_or_empty(object()) == {}
