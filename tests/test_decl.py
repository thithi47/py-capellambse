# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import io
import pathlib
import shutil
import subprocess
import sys
import textwrap
from importlib import metadata as imm

import pytest

import capellambse
from capellambse import decl, helpers
from capellambse.loader import modelinfo

# pylint: disable-next=relative-beyond-top-level, useless-suppression
from .conftest import (  # type: ignore[import]
    INSTALLED_PACKAGE,
    TEST_MODEL,
    TEST_ROOT,
)

DATAPATH = pathlib.Path(__file__).parent / "data" / "decl"
MODELPATH = pathlib.Path(TEST_ROOT / "5_0")

ROOT_COMPONENT = helpers.UUIDString("0d2edb8f-fa34-4e73-89ec-fb9a63001440")
ROOT_FUNCTION = helpers.UUIDString("f28ec0f8-f3b3-43a0-8af7-79f194b29a2d")
METADATA = {
    "capellambse": "1.0.0",
    "model": {"url": "Example.com", "version": 12345678},
    "referencing": "explicit",
    "generator": "Example 1.0.0",
}


class TestDumpLoad:
    @staticmethod
    def test_promises_are_serialized_with_promise_tag():
        id = "some-future-object"
        data = [{"parent": decl.Promise(id)}]
        expected = f"- parent: !promise {id!r}\n"

        actual = decl.dump(data)

        assert actual == expected

    @staticmethod
    def test_uuid_references_are_serialized_with_uuid_tag():
        uuid = helpers.UUIDString("00000000-0000-0000-0000-000000000000")
        data = [{"parent": decl.UUIDReference(uuid)}]
        expected = f"- parent: !uuid {uuid!r}\n"

        actual = decl.dump(data)

        assert actual == expected

    @staticmethod
    def test_promise_tags_are_deserialized_as_promise():
        id = "some-future-object"
        yaml = f"- parent: !promise {id!r}\n"
        expected = [{"parent": decl.Promise(id)}]

        actual = decl.load(io.StringIO(yaml))

        assert actual == expected

    @staticmethod
    def test_uuid_tags_are_deserialized_as_uuidreference():
        uuid = helpers.UUIDString("00000000-0000-0000-0000-000000000000")
        yaml = f"- parent: !uuid {uuid!r}\n"
        expected = [{"parent": decl.UUIDReference(uuid)}]

        actual = decl.load(io.StringIO(yaml))

        assert actual == expected

    @staticmethod
    def test_dumping_with_metadata():
        uuid = helpers.UUIDString("00000000-0000-0000-0000-000000000000")
        data = [{"parent": decl.UUIDReference(uuid)}]

        decl.dump(data, metadata=METADATA)

    @staticmethod
    def test_loading_with_metadata():
        uuid = helpers.UUIDString("00000000-0000-0000-0000-000000000000")
        yml = textwrap.dedent(
            f"""\
            capellambse: 1.0.0
            model:
              version: 12345678
              url: Example.com
            referencing: explicit
            generator: Example 1.0.0
            ---
            - parent: !uuid {uuid!r}
            """
        )
        expected = [METADATA, [{"parent": decl.UUIDReference(uuid)}]]

        metadata, actual = decl.load_with_metadata(io.StringIO(yml))

        assert [metadata, actual] == expected


class TestApplyExtend:
    @staticmethod
    def test_decl_errors_on_unknown_operations(
        model: capellambse.MelodyModel,
    ) -> None:
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              invalid_operation: {{}}
            """

        with pytest.raises(ValueError, match="invalid_operation"):
            decl.apply(model, io.StringIO(yml), strict=False)

    @staticmethod
    @pytest.mark.parametrize(
        ["parent_str", "parent_getter"],
        [
            pytest.param(
                f"!uuid {ROOT_FUNCTION}",
                lambda m: m.by_uuid(ROOT_FUNCTION),
                id="!uuid",
            ),
        ],
    )
    def test_decl_finds_parent_to_act_on(
        model: capellambse.MelodyModel, parent_str, parent_getter
    ) -> None:
        funcname = "pass the unit test"
        yml = f"""\
            - parent: {parent_str}
              extend:
                functions:
                  - name: {funcname!r}
            """
        expected_len = len(model.search()) + 1
        assert funcname not in parent_getter(model).functions.by_name

        decl.apply(model, io.StringIO(yml), strict=False)

        actual_len = len(model.search())
        assert actual_len == expected_len
        assert funcname in parent_getter(model).functions.by_name

    @staticmethod
    def test_decl_creates_each_object_in_a_list(
        model: capellambse.MelodyModel,
    ) -> None:
        parent_obj = model.by_uuid(ROOT_FUNCTION)
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: pass the first test
                  - name: pass the second test
                  - name: pass the third test
            """
        expected_len = len(model.search()) + 3
        for i in ("first", "second", "third"):
            assert f"pass the {i} test" not in parent_obj.functions.by_name

        decl.apply(model, io.StringIO(yml), strict=False)

        actual_len = len(model.search())
        assert actual_len == expected_len
        for i in ("first", "second", "third"):
            assert f"pass the {i} test" in parent_obj.functions.by_name

    @staticmethod
    def test_decl_creates_nested_complex_objects_where_they_belong(
        model: capellambse.MelodyModel,
    ) -> None:
        root = model.by_uuid(ROOT_FUNCTION)
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: pass the unit test
                    functions:
                      - name: run the test function
                      - name: make assertions
            """
        expected_len = len(model.search()) + 3

        decl.apply(model, io.StringIO(yml), strict=False)

        actual_len = len(model.search())
        assert actual_len == expected_len
        assert "pass the unit test" in root.functions.by_name
        parent = root.functions.by_name("pass the unit test", single=True)
        assert "run the test function" in parent.functions.by_name
        assert "make assertions" in parent.functions.by_name

    @staticmethod
    @pytest.mark.parametrize(
        "type",
        ["AttributeDefinition", "AttributeDefinitionEnumeration"],
    )
    def test_decl_can_disambiguate_creations_with_type_hints(
        model: capellambse.MelodyModel, type: str
    ) -> None:
        module_id = "db47fca9-ddb6-4397-8d4b-e397e53d277e"
        module = model.by_uuid(module_id)
        yml = f"""\
            - parent: !uuid {module_id}
              extend:
                attribute_definitions:
                  - long_name: New attribute
                    _type: {type}
            """
        assert "New attribute" not in module.attribute_definitions.by_long_name

        decl.apply(model, io.StringIO(yml), strict=False)

        attrdefs = module.attribute_definitions
        assert "New attribute" in attrdefs.by_long_name
        newdef = attrdefs.by_long_name("New attribute", single=True)
        assert newdef.xtype.endswith(f":{type}")

    @staticmethod
    def test_decl_can_create_simple_objects_by_passing_plain_strings(
        model: capellambse.MelodyModel,
    ) -> None:
        attrdef_id = "637caf95-3229-4607-99a0-7d7b990bc97f"
        attrdef = model.by_uuid(attrdef_id)
        yml = f"""\
            - parent: !uuid {attrdef_id}
              extend:
                values:
                  - NewGame++
            """
        assert "NewGame++" not in attrdef.values

        decl.apply(model, io.StringIO(yml), strict=False)

        assert "NewGame++" in attrdef.values

    @staticmethod
    def test_extend_operations_change_model_objects_in_place(
        model: capellambse.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        fnc = model.by_uuid("8833d2dc-b862-4a50-b26c-6f7e0f17faef")
        old_parent = fnc.parent
        assert old_parent != root_function
        assert fnc not in root_function.functions
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - !uuid {fnc.uuid}
            """

        decl.apply(model, io.StringIO(yml), strict=False)

        assert fnc in root_function.functions
        assert root_function == fnc.parent

    @staticmethod
    def test_extend_operations_with_promises_change_model_objects_in_place(
        model: capellambse.MelodyModel,
    ) -> None:
        root_component = model.by_uuid(ROOT_COMPONENT)
        fnc_name = "The promised one"
        assert fnc_name not in root_component.functions.by_name
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: {fnc_name}
                    promise_id: promised-fnc
            - parent: !uuid {ROOT_COMPONENT}
              extend:
                functions:
                  - !promise promised-fnc
            """

        decl.apply(model, io.StringIO(yml), strict=False)

        assert fnc_name in root_component.functions.by_name

    @staticmethod
    def test_extend_operations_on_faulty_attribute_cause_an_exception(
        model: capellambse.MelodyModel,
    ) -> None:
        non_existing_attr = "Thought up"
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              extend:
                {non_existing_attr}:
                  - !uuid {ROOT_FUNCTION}
            """

        with pytest.raises(TypeError, match=non_existing_attr):
            decl.apply(model, io.StringIO(yml), strict=False)


class TestApplyPromises:
    @staticmethod
    def test_promises_can_backwards_reference_objects(
        model: capellambse.MelodyModel,
    ) -> None:
        root_func = model.by_uuid(ROOT_FUNCTION)
        root_comp = model.by_uuid(ROOT_COMPONENT)
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: pass the unit test
                    promise_id: pass-test
            - parent: !uuid {ROOT_COMPONENT}
              extend:
                allocated_functions:
                  - !promise pass-test
            """
        expected_len = len(root_comp.allocated_functions) + 1

        decl.apply(model, io.StringIO(yml), strict=False)

        actual_len = len(root_comp.allocated_functions)
        assert actual_len == expected_len
        assert "pass the unit test" in root_func.functions.by_name
        assert "pass the unit test" in root_comp.allocated_functions.by_name

    @staticmethod
    def test_promises_can_forward_reference_objects(
        model: capellambse.MelodyModel,
    ) -> None:
        root_func = model.by_uuid(ROOT_FUNCTION)
        root_comp = model.by_uuid(ROOT_COMPONENT)
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              extend:
                allocated_functions:
                  - !promise pass-test
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: pass the unit test
                    promise_id: pass-test
            """
        expected_len = len(root_comp.allocated_functions) + 1

        decl.apply(model, io.StringIO(yml), strict=False)

        actual_len = len(root_comp.allocated_functions)
        assert actual_len == expected_len
        assert "pass the unit test" in root_func.functions.by_name
        assert "pass the unit test" in root_comp.allocated_functions.by_name

    @staticmethod
    @pytest.mark.parametrize(
        "order",
        [
            pytest.param((0, 1), id="backward"),
            pytest.param((1, 0), id="forward"),
        ],
    )
    def test_promises_on_simple_attributes_can_reference_objects(
        model: capellambse.MelodyModel, order
    ) -> None:
        root_func = model.by_uuid(ROOT_FUNCTION)
        snippets = (
            f"""
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                inputs:
                  - name: My input
                    promise_id: inport
                outputs:
                  - name: My output
                    promise_id: outport
            """,
            f"""
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                exchanges:
                  - name: Test exchange
                    source: !promise outport
                    target: !promise inport
            """,
        )
        yml = snippets[order[0]] + snippets[order[1]]

        decl.apply(model, io.StringIO(yml), strict=False)

        assert "Test exchange" in root_func.exchanges.by_name
        exc = root_func.exchanges.by_name("Test exchange")
        assert exc.source == root_func.outputs.by_name("My output")
        assert exc.target == root_func.inputs.by_name("My input")

    @staticmethod
    def test_reused_promise_ids_cause_an_exception(
        model: capellambse.MelodyModel,
    ) -> None:
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: pass the first unit test
                    promise_id: colliding-promise-id
                  - name: pass the second unit test
                    promise_id: colliding-promise-id
            """

        with pytest.raises(ValueError, match=r"\bcolliding-promise-id\b"):
            decl.apply(model, io.StringIO(yml), strict=False)

    @staticmethod
    def test_unfulfilled_promises_raise_an_exception(
        model: capellambse.MelodyModel,
    ) -> None:
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              extend:
                allocated_functions:
                  - !promise pass-test
            """

        with pytest.raises(decl.UnfulfilledPromisesError, match="^pass-test$"):
            decl.apply(model, io.StringIO(yml), strict=False)


class TestApplyModify:
    @staticmethod
    def test_modify_operations_change_model_objects_in_place(
        model: capellambse.MelodyModel,
    ) -> None:
        newname = "Coffee machine"
        root_component = model.by_uuid(ROOT_COMPONENT)
        assert root_component.name != newname
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              modify:
                name: {newname}
            """

        decl.apply(model, io.StringIO(yml), strict=False)

        assert root_component.name == newname

    @staticmethod
    def test_modify_can_set_attributes_to_promises(
        model: capellambse.MelodyModel,
    ) -> None:
        root_component = model.by_uuid(ROOT_COMPONENT)
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              modify:
                allocated_functions:
                  - !promise make-coffee
            - parent: !uuid {ROOT_FUNCTION}
              extend:
                functions:
                  - name: make coffee
                    promise_id: make-coffee
            """
        assert "make coffee" not in root_component.allocated_functions.by_name

        decl.apply(model, io.StringIO(yml), strict=False)

        assert "make coffee" in root_component.allocated_functions.by_name

    @staticmethod
    def test_modify_can_set_attributes_to_uuid_references(
        model: capellambse.MelodyModel,
    ) -> None:
        root_component = model.by_uuid(ROOT_COMPONENT)
        root_function = model.by_uuid(ROOT_FUNCTION)
        yml = f"""\
            - parent: !uuid {ROOT_COMPONENT}
              modify:
                allocated_functions:
                  - !uuid {ROOT_FUNCTION}
            """
        assert root_function not in root_component.allocated_functions

        decl.apply(model, io.StringIO(yml), strict=False)

        assert root_function in root_component.allocated_functions

    @staticmethod
    def test_modifying_to_a_list_removes_all_previous_list_members(
        model: capellambse.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              modify:
                functions:
                  - name: survive
            """
        assert len(root_function.functions) > 0

        decl.apply(model, io.StringIO(yml), strict=False)

        assert len(root_function.functions) == 1
        assert root_function.functions[0].name == "survive"


class TestApplyDelete:
    @staticmethod
    def test_delete_operations_remove_child_objects_from_the_model(
        model: capellambse.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        assert len(root_function.functions) > 0
        subfunc: str = root_function.functions[0].uuid
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              delete:
                functions:
                  - !uuid {subfunc}
            """
        assert subfunc in root_function.functions.by_uuid
        expected_len = len(root_function.functions) - 1

        decl.apply(model, io.StringIO(yml), strict=False)

        assert len(root_function.functions) == expected_len
        assert subfunc not in root_function.functions.by_uuid
        with pytest.raises(KeyError, match=subfunc):
            model.by_uuid(subfunc)

    @staticmethod
    def test_delete_operations_delete_attributes_if_no_list_of_uuids_was_given(
        model: capellambse.MelodyModel,
    ) -> None:
        root_function = model.by_uuid(ROOT_FUNCTION)
        assert len(root_function.functions) > 0
        yml = f"""\
            - parent: !uuid {ROOT_FUNCTION}
              delete:
                functions:
            """

        decl.apply(model, io.StringIO(yml), strict=False)

        assert len(root_function.functions) == 0


class TestMetadataMatchesModelinfo:
    @staticmethod
    def test_current_version_less_than_received_version(
        model: capellambse.MelodyModel,
    ):
        metadata = {"capellambse": "1.2.3"}
        version = imm.version("capellambse")

        with pytest.raises(ValueError) as excinfo:
            decl._metadata_matches_modelinfo(model, metadata)

        assert str(excinfo.value) == (
            "Unsupported change-set: The version of the installed capellambse "
            f"({version}) is lower than the version with which the change-set "
            "was written with (1.2.3)."
        )

    @staticmethod
    def test_referencing_not_explicit(model: capellambse.MelodyModel):
        metadata = {
            "capellambse": imm.version("capellambse"),
            "referencing": "implicit",
        }

        with pytest.raises(ValueError) as excinfo:
            decl._metadata_matches_modelinfo(model, metadata)

        assert str(excinfo.value) == (
            "Unsupported change-set: Only explicit change-sets are supported. "
            "Got 'referencing: implicit'."
        )

    @staticmethod
    def test_revision_hash_not_matching(
        model: capellambse.MelodyModel, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            model._loader,
            "get_model_info",
            lambda: modelinfo.ModelInfo(rev_hash="abc123"),
        )
        metadata = {
            "capellambse": imm.version("capellambse"),
            "referencing": "explicit",
            "model": {"version": "def456"},
        }

        with pytest.raises(ValueError) as excinfo:
            decl._metadata_matches_modelinfo(model, metadata)

        assert str(excinfo.value) == (
            "Unsupported change-set: Model revision hash isn't matching. Got "
            "'def456' but current is 'abc123'."
        )

    @staticmethod
    def test_model_url_not_matching(
        model: capellambse.MelodyModel, monkeypatch: pytest.MonkeyPatch
    ):
        url = "https://example.com/models/123"
        monkeypatch.setattr(
            model._loader,
            "get_model_info",
            lambda: modelinfo.ModelInfo(url=url),
        )
        expected_url = "https://example.com/models/456"
        metadata = {
            "capellambse": imm.version("capellambse"),
            "referencing": "explicit",
            "model": {"url": expected_url, "version": None},
        }

        with pytest.raises(ValueError) as excinfo:
            decl._metadata_matches_modelinfo(model, metadata)

        assert str(excinfo.value) == (
            "Unsupported change-set: Model URL isn't matching. Got "
            f"{expected_url!r} but current is {url!r}."
        )


@pytest.mark.parametrize("filename", ["coffee-machine.yml"])
def test_full_example(model: capellambse.MelodyModel, filename: str):
    decl.apply(model, DATAPATH / filename, strict=False)


@pytest.mark.parametrize("filename", ["coffee-machine.yml"])
def test_apply_fails_on_missing_metadata(
    model: capellambse.MelodyModel, filename: str
):
    _, instructions = decl.load_with_metadata(DATAPATH / filename)
    yml = decl.dump(instructions)

    with pytest.raises(ValueError) as error:
        decl.apply(model, io.StringIO(yml), strict=True)

    assert str(error.value) == "No metadata found."


def test_cli_applies_a_yaml_and_saves_the_model_back(tmp_path: pathlib.Path):
    shutil.copytree(MODELPATH, tmp_path / "model")
    model = tmp_path / "model" / TEST_MODEL
    semmodel = model.with_suffix(".capella")
    oldhash = hashlib.sha256(semmodel.read_bytes()).hexdigest()
    declfile = patch_metadata(DATAPATH / "coffee-machine.yml", model, tmp_path)

    cli = subprocess.run(
        [sys.executable, "-mcapellambse.decl", f"--model={model}", declfile],
        cwd=INSTALLED_PACKAGE.parent,
        check=False,
    )

    assert cli.returncode == 0, "CLI process exited unsuccessfully"
    newhash = hashlib.sha256(semmodel.read_bytes()).hexdigest()
    assert newhash != oldhash, "Files on disk didn't change"


def patch_metadata(
    decl_path: pathlib.Path, model_path: pathlib.Path, tmp_path: pathlib.Path
) -> pathlib.Path:
    model = capellambse.MelodyModel(model_path)
    metadata, instructions = decl.load_with_metadata(decl_path)
    metadata["capellambse"] = imm.version("capellambse")
    metadata["model"]["version"] = model.info.rev_hash
    metadata["model"]["url"] = model.info.url
    yml = decl.dump(instructions, metadata=metadata)
    new_path = tmp_path / decl_path.name
    new_path.write_text(yml, encoding="utf8")
    return new_path
