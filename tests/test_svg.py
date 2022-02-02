# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import collections.abc as cabc
import json
import logging
import math
import pathlib
import random
import string

import cssutils
import pytest
from lxml import etree
from svgwrite import container, shapes, text

import capellambse
from capellambse.svg import (
    SVGDiagram,
    decorations,
    generate,
    helpers,
    style,
    symbols,
)

cssutils.log.setLevel(logging.CRITICAL)

TEST_LAB = "[LAB] Wizzard Education"
TEST_DIAGS = [
    TEST_LAB,
    "[OAB] Operational Context",
    "[OCB] Operational Capabilities",
    "[OPD] Obtain food via hunting",
    "[MSM] States of Functional Human Being",
    "[OEBD] Operational Context",
    "[PAB] Physical System",
    "[LDFB] Test flow",
    "[CC] Capability",
]
TEST_DECO = set(style.STATIC_DECORATIONS.keys()) - {"__GLOBAL__"}
FREE_SYMBOLS = {
    "OperationalCapabilitySymbol",
    "AndControlNodeSymbol",
    "ItControlNodeSymbol",
    "OrControlNodeSymbol",
    "FinalStateSymbol",
    "InitialPseudoStateSymbol",
    "TerminatePseudoStateSymbol",
    "StickFigureSymbol",
}


@pytest.fixture(name="tmp_json")
def tmp_json_fixture(
    model: capellambse.MelodyModel, tmp_path: pathlib.Path
) -> pathlib.Path:
    """Return tmp path of diagram json file"""
    dest = tmp_path / (TEST_LAB + ".json")
    diagram_json: str = model.diagrams.by_name(TEST_LAB).render("json_pretty")
    dest.write_text(diagram_json)
    return dest


class TestSVG:
    def test_diagram_meta_data_attributes(
        self, tmp_json: pathlib.Path
    ) -> None:
        diag_meta = generate.DiagramMetadata.from_dict(
            json.loads(tmp_json.read_text())
        )
        assert diag_meta.name == TEST_LAB
        assert diag_meta.pos == (10, 10)
        assert diag_meta.size == (1162, 611)
        assert diag_meta.viewbox == "10 10 1162 611"
        assert diag_meta.class_ == "Logical Architecture Blank"

    def test_diagram_from_json_path_componentports(
        self, tmp_json: pathlib.Path
    ) -> None:
        tree = etree.fromstring(
            SVGDiagram.from_json_path(tmp_json).to_string()
        )

        cp_in_exists: bool = False
        cp_inout_exists: bool = False
        cp_out_exists: bool = False
        cp_unset_exists: bool = False
        cp_reference_exists: bool = False

        for item in tree.iter():
            # The class CP should not exist anymore as it has been replaced with
            # CP_IN, CP_OUT, CP_UNSET or CP_INOUT
            assert item.get("class") != "Box CP"

            # Check that the classes CP_IN, CP_OUT, CP_UNSET and CP_INOUT exist
            if item.get("class") == "Box CP_IN":
                cp_in_exists = True
            elif item.get("class") == "Box CP_OUT":
                cp_out_exists = True
            elif item.get("class") == "Box CP_INOUT":
                cp_inout_exists = True
            elif item.get("class") == "Box CP_UNSET":
                cp_unset_exists = True

            # Check that reference symbol for CP exists
            if (
                item.tag == "{http://www.w3.org/2000/svg}symbol"
                and item.get("id") == "ComponentPortSymbol"
            ):
                cp_reference_exists = True

        assert cp_in_exists
        assert cp_out_exists
        assert cp_inout_exists
        assert cp_reference_exists

    @pytest.fixture
    def tmp_svg(self, tmp_path: pathlib.Path) -> SVGDiagram:
        name = "Test svg"
        meta = generate.DiagramMetadata(
            pos=(0, 0), size=(1, 1), name=name, class_="TEST"
        )
        svg = SVGDiagram(meta, [])
        svg.drawing.filename = str(tmp_path / name)
        return svg

    def test_diagram_saves(self, tmp_svg: SVGDiagram) -> None:
        tmp_svg.save_drawing()
        assert pathlib.Path(tmp_svg.drawing.filename).is_file()

    # FIXME: change this to a parametrized test, do not use if- or for-statements in a unit test
    def test_css_colors(self, tmp_json: pathlib.Path) -> None:
        COLORS_TO_CHECK = {
            ".LogicalArchitectureBlank g.Box.CP_IN > line": {
                "stroke": "#000000"
            },
            ".LogicalArchitectureBlank g.Box.CP_IN > rect, .LogicalArchitectureBlank g.Box.CP_IN > use": {
                "fill": "#FFFFFF",
                "stroke": "#000000",
            },
            ".LogicalArchitectureBlank g.Box.CP_OUT > line": {
                "stroke": "#000000"
            },
            ".LogicalArchitectureBlank g.Box.CP_OUT > rect, .LogicalArchitectureBlank g.Box.CP_OUT > use": {
                "fill": "#FFFFFF",
                "stroke": "#000000",
            },
            ".LogicalArchitectureBlank g.Box.CP_INOUT > line": {
                "stroke": "#000000,"
            },
            ".LogicalArchitectureBlank g.Box.CP_INOUT > rect, .LogicalArchitectureBlank g.Box.CP_INOUT > use": {
                "fill": "#FFFFFF",
                "stroke": "#000000",
            },
            ".LogicalArchitectureBlank g.Edge > path": {
                "fill": "none",
                "stroke": "rgb(0, 0, 0)",
            },
            ".LogicalArchitectureBlank g.Box > line": {"stroke": "#000000"},
            ".LogicalArchitectureBlank g.Box > rect, .LogicalArchitectureBlank g.Box > use": {
                "fill": "transparent",
                "stroke": "#000000",
            },
            ".LogicalArchitectureBlank g.Box.Annotation > line": {
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Box.Annotation > rect, .LogicalArchitectureBlank g.Box.Annotation > use": {
                "fill": "none",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Box.Constraint > line": {
                "stroke": "#888888",
            },
            ".LogicalArchitectureBlank g.Box.Constraint > rect, .LogicalArchitectureBlank g.Box.Constraint > use": {
                "fill": "#FFF5B5",
                "stroke": "#888888",
            },
            ".LogicalArchitectureBlank g.Box.Constraint > text": {
                "fill": "#000000"
            },
            ".LogicalArchitectureBlank g.Box.Note > line": {
                "stroke": "#FFCC66"
            },
            ".LogicalArchitectureBlank g.Box.Note > rect, .LogicalArchitectureBlank g.Box.Note > use": {
                "fill": " #FFFFCB",
                "stroke": " #FFCC66",
            },
            ".LogicalArchitectureBlank g.Box.Note > text": {
                "fill": "#000000",
            },
            ".LogicalArchitectureBlank g.Box.Requirement > line": {
                "stroke": "#72496E",
            },
            ".LogicalArchitectureBlank g.Box.Requirement > rect, .LogicalArchitectureBlank g.Box.Requirement > use": {
                "fill": "#D9C4D7",
                "stroke": "#72496E",
            },
            ".LogicalArchitectureBlank g.Box.Requirement > text": {
                "fill": "#000000",
            },
            ".LogicalArchitectureBlank g.Box.Text > line": {
                "stroke": "transparent",
            },
            ".LogicalArchitectureBlank g.Box.Text > rect, .LogicalArchitectureBlank g.Box.Text > use": {
                "stroke": "transparent",
            },
            ".LogicalArchitectureBlank g.Edge > rect": {
                "fill": "none",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Circle > circle": {
                "fill": "#000000",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Edge.Connector > rect": {
                "fill": "none",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Circle.Connector > circle": {
                "fill": "#B0B0B0",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Edge.Connector > path": {
                "stroke": "#B0B0B0",
            },
            ".LogicalArchitectureBlank g.Edge.Constraint > rect": {
                "fill": "none",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Circle.Constraint > circle": {
                "fill": "#000000",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Edge.Constraint > path": {
                "stroke": "#000000",
            },
            ".LogicalArchitectureBlank g.Edge.Note > rect": {
                "fill": "none",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Circle.Note > circle": {
                "fill": "#000000",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Edge.Note > path": {
                "stroke": "#000000",
            },
            ".LogicalArchitectureBlank g.Edge.RequirementRelation > rect": {
                "fill": "none",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Circle.RequirementRelation > circle": {
                "fill": "#72496E",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Edge.RequirementRelation > path": {
                "stroke": "#72496E"
            },
            ".LogicalArchitectureBlank g.Edge.RequirementRelation > text": {
                "fill": "#72496E",
            },
            ".LogicalArchitectureBlank g.Box.CP > line": {
                "stroke": "#000000",
            },
            ".LogicalArchitectureBlank g.Box.CP > rect, .LogicalArchitectureBlank g.Box.CP > use": {
                "fill": "#FFFFFF",
                "stroke": "#000000",
            },
            ".LogicalArchitectureBlank g.Box.FIP > rect, .LogicalArchitectureBlank g.Box.FIP > use": {
                "fill": "#E08503",
            },
            ".LogicalArchitectureBlank g.Box.FOP > rect, .LogicalArchitectureBlank g.Box.FOP > use": {
                "fill": "#095C2E",
            },
            ".LogicalArchitectureBlank g.Box.LogicalActor > line": {
                "stroke": "#4A4A97",
            },
            ".LogicalArchitectureBlank g.Box.LogicalActor > text": {
                "fill": "#000000",
            },
            ".LogicalArchitectureBlank g.Box.LogicalComponent > line": {
                "stroke": "#4A4A97",
            },
            ".LogicalArchitectureBlank g.Box.LogicalComponent > text": {
                "fill": "#4A4A97",
            },
            ".LogicalArchitectureBlank g.Box.LogicalFunction > line": {
                "stroke": "#095C2E",
            },
            ".LogicalArchitectureBlank g.Box.LogicalFunction > rect, .LogicalArchitectureBlank g.Box.LogicalFunction > use": {
                "fill": "#C5FFA6",
                "stroke": "#095C2E",
            },
            ".LogicalArchitectureBlank g.Box.LogicalFunction > text": {
                "fill": "#095C2E",
            },
            ".LogicalArchitectureBlank g.Edge.FunctionalExchange > rect": {
                "fill": "none",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Circle.FunctionalExchange > circle": {
                "fill": "#095C2E",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Edge.FunctionalExchange > path": {
                "stroke": "#095C2E",
            },
            ".LogicalArchitectureBlank g.Edge.FunctionalExchange > text": {
                "fill": "#095C2E",
            },
            ".LogicalArchitectureBlank g.Edge.ComponentExchange > rect": {
                "fill": "none",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Circle.ComponentExchange > circle": {
                "fill": "#4A4A97",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Edge.ComponentExchange > path": {
                "stroke": "#4A4A97",
            },
            ".LogicalArchitectureBlank g.Edge.ComponentExchange > text": {
                "fill": "#4A4A97",
            },
            ".LogicalArchitectureBlank g.Edge.FIPAllocation > rect": {
                "fill": "none",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Circle.FIPAllocation > circle": {
                "fill": "#E08503",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Edge.FIPAllocation > path": {
                "stroke": "#E08503",
            },
            ".LogicalArchitectureBlank g.Edge.FOPAllocation > rect": {
                "fill": "none",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Circle.FOPAllocation > circle": {
                "fill": "#095C2E",
                "stroke": "none",
            },
            ".LogicalArchitectureBlank g.Edge.FOPAllocation > path": {
                "stroke": "#095C2E",
            },
        }

        tree = etree.fromstring(
            SVGDiagram.from_json_path(tmp_json).to_string()
        )
        style_ = tree.xpath(
            "/x:svg/x:defs/x:style",
            namespaces={"x": "http://www.w3.org/2000/svg"},
        )[0]

        stylesheet = cssutils.parseString(style_.text)
        for rule in stylesheet:
            for (element, prop) in COLORS_TO_CHECK.items():
                if (
                    rule.type == rule.STYLE_RULE
                    and rule.selectorText == element
                ):
                    for key, val in prop.items():
                        try:
                            property_value = rule.style.getProperty(
                                key
                            ).propertyValue.value
                        except AttributeError:
                            # FIXME: rules are duplicated with different values -> should be merged first
                            print(f"Missing attribute {key}")
                            continue
                        if val == "none":
                            assert property_value == "none"
                        elif key in ["fill", "stroke"]:
                            assert (
                                property_value
                                == cssutils.css.ColorValue(val).value
                            )
                        else:
                            raise NotImplementedError

    @pytest.mark.parametrize("diagram_name", TEST_DIAGS)
    def test_diagram_decorations(
        self, model: capellambse.MelodyModel, diagram_name: str
    ):
        """Test diagrams get rendered successfully"""
        diag = model.diagrams.by_name(diagram_name)
        diag.render("svg")

    @pytest.mark.parametrize("diagram_type", TEST_DECO)
    @pytest.mark.parametrize(
        "label",
        ["short test label", " ".join(string.ascii_letters)],
    )
    @pytest.mark.parametrize(
        "width,height", [(200, 150), (100, 300), (50, 300), (50, 50)]
    )
    @pytest.mark.skip("Currently broken")
    def test_box_contains_label_and_symbol_and_icons_dont_overlap_with_text(
        self, diagram_type: str, label: str, width: int, height: int
    ) -> None:
        """For all registered Diagramtypes with decorations test label and icon
        containment for boxes exclusively, i.e. exclude the following:
            * Ports
            * Exchanges
            * Markers

        If the label check fails the diagram gets saved to root directory for
        convinient investigation.
        """
        decos = [
            symbol
            for symbol in style.STATIC_DECORATIONS[diagram_type]
            if not "Port" in symbol
            and not "Mark" in symbol
            and not ("Exchange" in symbol or "Link" in symbol)
            and symbol not in FREE_SYMBOLS
        ]
        contents: cabc.Sequence[generate.ContentsDict] = [
            {
                "type": "box",
                "id": str(i),
                "class": symbol.split("Symbol")[0],
                "x": 10 + i * (width + 10),
                "y": 10,
                "width": width,
                "height": height,
                "label": label,
            }
            for i, symbol in enumerate(decos)
        ]
        meta = generate.DiagramMetadata.from_dict(
            {
                "name": f"SVGBoxLabelTest-{diagram_type}-{width}x{height}-{label}",
                "class": diagram_type,
                "x": 0,
                "y": 0,
                "width": len(contents) * (width + 10),
                "height": height + 50,
                "contents": contents,
            }
        )
        diagram = SVGDiagram(meta, contents)
        assert len(diagram.drawing.elements) == len(contents) + 2
        for elt in diagram.drawing.elements[2:]:
            assert isinstance(elt, container.Group)
            try:
                self.check_label_for_containment_and_overlap(*elt.elements)
            except AssertionError as error:
                diagram.save_drawing(True)
                raise error

    @pytest.mark.parametrize("diagram_type", TEST_DECO)
    @pytest.mark.parametrize(
        "label",
        ["short test label", " ".join(string.ascii_letters)],
    )
    @pytest.mark.parametrize(
        "width,height", [(50, 20), (100, 20), (20, 50), (20, 20)]
    )
    @pytest.mark.skip("Currently broken")
    def test_edge_contains_label_and_symbol_and_icons_dont_overlap_with_text(
        self, diagram_type: str, label: str, width: int, height: int
    ) -> None:
        """For all registered Diagramtypes with decorations test edge-symbols on
        not overlapping/overflowing into label text.
        """
        decos = [
            symbol
            for symbol in style.STATIC_DECORATIONS[diagram_type]
            if "Exchange" in symbol or "Link" in symbol
        ]
        contents: cabc.Sequence[generate.ContentsDict] = [
            {
                "type": "edge",
                "id": str(i),
                "class": symbol.split("Symbol")[0],
                "points": [
                    [random.randint(0, 300), random.randint(0, 300)],
                    [random.randint(0, 300), random.randint(0, 300)],
                ],
                "label": {
                    "x": 10 + i * (width + 20),
                    "y": 10,
                    "width": width,
                    "height": height,
                    "text": label,
                },
            }
            for i, symbol in enumerate(decos)
        ]
        meta = generate.DiagramMetadata.from_dict(
            {
                "name": f"SVGEdgeLabelTest-{diagram_type}-{width}x{height}-{label}",
                "class": diagram_type,
                "x": 0,
                "y": 0,
                "width": len(contents) * (width + 20),
                "height": 300,
                "contents": contents,
            }
        )
        diagram = SVGDiagram(meta, contents)
        assert len(diagram.drawing.elements) == len(contents) + 2
        for elt in diagram.drawing.elements[2:]:
            assert isinstance(elt, container.Group)
            _, bb, txt, symbol = elt.elements
            try:
                bb.attribs["width"] += (
                    symbol.attribs["width"] - 1 * decorations.icon_padding
                )
                bb.attribs["x"] -= (
                    symbol.attribs["width"] - 1 * decorations.icon_padding
                )
                self.check_label_for_containment_and_overlap(bb, txt, symbol)
            except AssertionError as error:
                diagram.save_drawing(True)
                raise error

    def check_label_for_containment_and_overlap(
        self, rect: shapes.Rect, txt: text.Text, symbol: container.Symbol
    ) -> None:
        right_bound = rect.attribs["x"] + rect.attribs["width"]
        lower_bound = rect.attribs["y"] + rect.attribs["height"]
        symbol_right_bound = symbol.attribs["x"] + symbol.attribs["width"]
        factor = 1.0
        text_anchor = txt.attribs.get("text-anchor", "start")
        if text_anchor == "middle":
            factor = 0.5

        # Check text is contained in box
        for tspan in txt.elements:
            # Check for horizontal overflow
            assert (
                rect.attribs["x"] <= float(tspan.attribs["x"]) <= right_bound
            )
            assert (
                float(tspan.attribs["x"])
                + factor * capellambse.helpers.extent_func(tspan.text)[0]
                <= right_bound + 2
            )
            # Check for vertical overflow
            assert (
                rect.attribs["y"] <= float(tspan.attribs["y"]) <= lower_bound
            )
            # Check that symbol doesn't overlap text
            if text_anchor == "middle":
                assert symbol_right_bound - 5.5 <= float(
                    tspan.attribs["x"]
                ) - 0.5 * math.floor(
                    capellambse.helpers.extent_func(tspan.text)[0]
                )
            else:
                assert symbol_right_bound <= float(tspan.attribs["x"])

        # Check symbol is contained in box
        # The leftest x-pos for symbol is rect.x - 2.5
        assert rect.attribs["x"] - 2.5 <= symbol.attribs["x"] <= right_bound
        assert symbol_right_bound <= right_bound
        assert rect.attribs["y"] - 5 <= symbol.attribs["y"] <= lower_bound
        assert symbol.attribs["y"] + symbol.attribs["height"] <= lower_bound


class TestSVGStylesheet:
    def test_svg_stylesheet_as_str(self, tmp_json) -> None:
        svg = SVGDiagram.from_json_path(tmp_json)
        for line in str(svg.drawing.stylesheet).splitlines():
            assert line.startswith(".LogicalArchitectureBlank")

    def test_svg_stylesheet_builder_fails_when_no_class_was_given(self):
        with pytest.raises(TypeError) as error:
            style.SVGStylesheet(None)  # type: ignore[arg-type]

        assert (
            error.value.args[0]
            == "Invalid type for class_ 'NoneType'. This needs to be a str."
        )


class TestDecoFactory:
    @pytest.mark.parametrize(
        "class_",
        ["LogicalComponentSymbol", "LogicalHumanActorSymbol", "EntitySymbol"],
    )
    def test_deco_factory_contains_styling_for_given_styleclass(
        self, class_: str
    ):
        assert class_ in decorations.deco_factories

    def test_deco_factory_returns_symbol_factory_for_given_styleclass(self):
        assert decorations.deco_factories["PortSymbol"] is symbols.port_symbol

    @pytest.mark.parametrize(
        "class_", ["ImaginaryClassSymbol", "NothingSymbol"]
    )
    def test_deco_factory_logs_error_when_not_containing_given_styleclass(
        self, caplog, class_: str
    ):
        assert class_ not in decorations.deco_factories
        assert (
            decorations.deco_factories[class_]
            is decorations.deco_factories["ErrorSymbol"]
        )
        with caplog.at_level(0, logger="decorations"):
            assert (
                caplog.messages[-1] == f"{class_} wasn't found in factories."
            )

    @pytest.mark.parametrize("attr", ["start", "translate", "offsets"])
    def test_making_linear_gradient_faulty_cases_raise_ValueError(
        self, attr: str
    ):
        params = {
            "id_": "test",
            attr: (0, 0, 0),
        }
        with pytest.raises(ValueError):
            symbols._make_lgradient(**params)

    def test_making_linear_gradient_with_translate(self):
        gradient = symbols._make_lgradient("test", translate=(0, 0))
        assert gradient.attribs.get("gradientTransform") == "translate(0 0)"


class TestSVGHelpers:
    def test_check_for_horizontal_overflow_recognizes_tabs_and_breaks(
        self,
    ) -> None:
        lines, margin, max_text_width = helpers.check_for_horizontal_overflow(
            "             • item 1\n             • item 2", 100, 0, 0
        )
        assert lines == ["             • item 1", "             • item 2"]
        assert 10 <= margin < 13
        for line in lines:
            assert capellambse.helpers.extent_func(line)[0] <= max_text_width
