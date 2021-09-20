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
"""Property Value Management extension for CapellaMBSE."""
from __future__ import annotations

import typing as t

from lxml import etree

import capellambse
import capellambse.model.common as c
import capellambse.pvmt.exceptions as pvexc


class PropertyValueProxy:
    """Provides access to an element's property values.

    Example for accessing property values on any object that has pvmt::

        >>> model.la.functions[0].pvmt['domain.group.property']
        'property'
        >>> model.la.functions[0].pvmt['domain.group']
        <pvmt.AppliedPropertyValueGroup "domain.group"(abcdef01-2345-6789-abcd-ef0123456789)>

    .. note::
        Access is only given if the PVMT Extension is successfully
        loaded on loading the model with the :class:`MelodyModel`.
    """

    _model: capellambse.MelodyModel
    _element: etree._Element

    @classmethod
    def from_model(
        cls, model: capellambse.MelodyModel, element: etree._Element
    ) -> PropertyValueProxy:
        """Create a PropertyValueProxy for an element."""
        if not hasattr(model, "_pvext") or model._pvext is None:
            raise AttributeError("Cannot access PVMT: extension is not loaded")

        self = cls.__new__(cls)
        self._model = model
        self._element = element
        return self

    def __init__(self, **kw: t.Any) -> None:
        raise TypeError("Cannot create PropertyValueProxy this way")

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._element is other._element

    def __getitem__(self, key):
        path = key.split(".")
        if len(path) < 1 or len(path) > 3:
            raise ValueError(
                "Provide a name as `domain`, `domain.group` or `domain.group.prop`"
            )

        domain = _PVMTDomain(self._model, self._element, path[0])
        if len(path) == 1:
            return domain
        else:
            return domain[".".join(path[1:])]


class _PVMTDomain:
    def __init__(
        self,
        model: capellambse.MelodyModel,
        element: etree._Element,
        domain: str,
    ):
        self._model = model
        self._element = element
        self._domain = domain

    def __getitem__(self, key):
        path = key.split(".")
        if len(path) < 1 or len(path) > 2:
            raise ValueError("Provide a name as `group` or `group.prop`")

        try:
            pvgroup = self._model._pvext.get_element_pv(
                self._element, f"{self._domain}.{path[0]}", create=False
            )
        except pvexc.GroupNotAppliedError:
            return None

        if len(path) == 1:
            return pvgroup
        else:
            return pvgroup[path[1]]

    def __repr__(self) -> str:
        return f"<PVMTDomain {self._domain!r} on {self._model!r}>"


def init() -> None:
    c.set_accessor(
        c.GenericElement, "pvmt", c.AlternateAccessor(PropertyValueProxy)
    )
