# SPDX-License-Identifier: MIT OR GPL-3.0-or-later
# SPDX-FileCopyrightText: 2018 iCyP
# SPDX-FileCopyrightText: 2024 saturday06
import json
import warnings
import webbrowser
from collections.abc import Set as AbstractSet
from pathlib import Path
from typing import TYPE_CHECKING, Optional, TypeVar, cast
from urllib.parse import urlparse

from bpy.app.translations import pgettext
from bpy.props import StringProperty
from bpy.types import (
    Armature,
    Context,
    Event,
    Operator,
    UILayout,
)
from bpy_extras.io_utils import ExportHelper, ImportHelper

from ..common.deep import make_json
from ..common.human_bone_mapper.vroid_mapping import (
    FULL_PATTERN,
    symmetrise_vroid_bone_name,
)
from ..common.logger import get_logger
from ..common.vrm0.human_bone import HumanBoneSpecifications
from ..common.workspace import save_workspace
from . import search
from .extension import get_armature_extension
from .t_pose import set_estimated_humanoid_t_pose

logger = get_logger(__name__)


class VRM_OT_simplify_vroid_bones(Operator):
    bl_idname = "vrm.bones_rename"
    bl_label = "Symmetrize VRoid Bone Names on X-Axis"
    bl_description = "Make VRoid bone names editable for X-axis mirroring."
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_object_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )

    def update_armature_name(self, _context: Context) -> None:
        message = (
            f"`{type(self).__qualname__}.armature_name` is deprecated"
            + " and will be removed in the next major release."
            + f" `Please use {type(self).__qualname__}.armature_object_name` instead."
        )
        logger.warning(message)
        warnings.warn(message, DeprecationWarning, stacklevel=5)

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        update=update_armature_name,
    )
    """`armature_name` is deprecated and will be removed in the next major release.
    Please use `armature_object_name` instead.
    """

    @staticmethod
    def vroid_bones_exist(armature: Armature) -> bool:
        return any(map(FULL_PATTERN.match, armature.bones.keys()))

    def execute(self, context: Context) -> set[str]:
        if not self.armature_object_name and self.armature_name:
            self.armature_object_name = self.armature_name
        armature = context.blend_data.objects.get(self.armature_object_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}

        with save_workspace(context):
            for bone_name, bone in armature_data.bones.items():
                bone.name = symmetrise_vroid_bone_name(bone_name)

        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # To regenerate, run the `uv run tools/property_typing.py` command.
        armature_object_name: str  # type: ignore[no-redef]
        armature_name: str  # type: ignore[no-redef]


class VRM_OT_save_human_bone_mappings(Operator, ExportHelper):
    bl_idname = "vrm.save_human_bone_mappings"
    bl_label = "Save Bone Mappings"
    bl_description = "Save bone mappings."
    bl_options: AbstractSet[str] = {"REGISTER"}

    filename_ext = ".json"
    filter_glob: StringProperty(  # type: ignore[valid-type]
        default="*.json",
        options={"HIDDEN"},
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        return search.armature_exists(context)

    def execute(self, context: Context) -> set[str]:
        armature = search.current_armature(context)
        if not armature:
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}

        mappings = {}
        for human_bone in get_armature_extension(
            armature_data
        ).vrm0.humanoid.human_bones:
            if human_bone.bone not in HumanBoneSpecifications.all_names:
                continue
            if not human_bone.node.bone_name:
                continue
            mappings[human_bone.bone] = human_bone.node.bone_name

        Path(self.filepath).write_bytes(
            json.dumps(mappings, sort_keys=True, indent=4)
            .replace("\r\n", "\n")
            .encode()
        )
        return {"FINISHED"}

    def invoke(self, context: Context, event: Event) -> set[str]:
        return ExportHelper.invoke(self, context, event)

    if TYPE_CHECKING:
        # This code is auto generated.
        # To regenerate, run the `uv run tools/property_typing.py` command.
        filter_glob: str  # type: ignore[no-redef]


class VRM_OT_load_human_bone_mappings(Operator, ImportHelper):
    bl_idname = "vrm.load_human_bone_mappings"
    bl_label = "Load Bone Mappings"
    bl_description = "Load bone mappings."
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    filename_ext = ".json"
    filter_glob: StringProperty(  # type: ignore[valid-type]
        default="*.json",
        options={"HIDDEN"},
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        return search.armature_exists(context)

    def execute(self, context: Context) -> set[str]:
        armature = search.current_armature(context)
        if not armature:
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}

        obj = make_json(json.loads(Path(self.filepath).read_text(encoding="UTF-8")))
        if not isinstance(obj, dict):
            return {"CANCELLED"}

        for human_bone_name, bpy_bone_name in obj.items():
            if human_bone_name not in HumanBoneSpecifications.all_names:
                continue
            if not isinstance(bpy_bone_name, str):
                continue
            # INFO@MICROSOFT.COM
            found = False
            for human_bone in get_armature_extension(
                armature_data
            ).vrm0.humanoid.human_bones:
                if human_bone.bone == human_bone_name:
                    human_bone.node.bone_name = bpy_bone_name
                    found = True
                    break
            if found:
                continue

            human_bone = get_armature_extension(
                armature_data
            ).vrm0.humanoid.human_bones.add()
            human_bone.bone = human_bone_name
            human_bone.node.bone_name = bpy_bone_name

        return {"FINISHED"}

    def invoke(self, context: Context, event: Event) -> set[str]:
        return ImportHelper.invoke(self, context, event)

    if TYPE_CHECKING:
        # This code is auto generated.
        # To regenerate, run the `uv run tools/property_typing.py` command.
        filter_glob: str  # type: ignore[no-redef]


class VRM_OT_open_url_in_web_browser(Operator):
    bl_idname = "vrm.open_url_in_web_browser"
    bl_label = "Open"
    bl_description = "Open the URL in the default web browser."
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    url: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"}
    )

    @staticmethod
    def supported(url_str: str) -> bool:
        try:
            url = urlparse(url_str)
        except ValueError:
            return False
        return url.scheme in ["http", "https"]

    def execute(self, _context: Context) -> set[str]:
        url = self.url
        if not self.supported(url):
            return {"CANCELLED"}
        webbrowser.open(self.url)
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # To regenerate, run the `uv run tools/property_typing.py` command.
        url: str  # type: ignore[no-redef]


class VRM_OT_show_blend_file_compatibility_warning(Operator):
    bl_idname = "vrm.show_blend_file_compatibility_warning"
    bl_label = "File Compatibility Warning"
    bl_description = "Show blend file compatibility warning."
    bl_options: AbstractSet[str] = {"REGISTER"}

    file_version: StringProperty(options={"HIDDEN"})  # type: ignore[valid-type]
    app_version: StringProperty(options={"HIDDEN"})  # type: ignore[valid-type]

    def execute(self, _context: Context) -> set[str]:
        return {"FINISHED"}

    def invoke(self, context: Context, _event: Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, _context: Context) -> None:
        column = self.layout.row(align=True).column()
        text = pgettext(
            "The current file is not compatible with the running Blender.\n"
            + "The current file was created in Blender {file_version}, but the running"
            + " Blender version is {app_version}.\n"
            + "This incompatibility may result in data loss or corruption."
        ).format(
            app_version=self.app_version,
            file_version=self.file_version,
        )
        description_outer_column = column.column()
        description_outer_column.emboss = "NONE"
        description_column = description_outer_column.box().column(align=True)
        for i, line in enumerate(text.splitlines()):
            icon = "ERROR" if i == 0 else "NONE"
            description_column.label(text=line, translate=False, icon=icon)
        open_url = layout_operator(
            self.layout,
            VRM_OT_open_url_in_web_browser,
            text="Open Documentation",
            icon="URL",
        )
        open_url.url = "https://developer.blender.org/docs/handbook/guidelines/compatibility_handling_for_blend_files/#forward-compatibility"

    if TYPE_CHECKING:
        # This code is auto generated.
        # To regenerate, run the `uv run tools/property_typing.py` command.
        file_version: str  # type: ignore[no-redef]
        app_version: str  # type: ignore[no-redef]


class VRM_OT_show_blend_file_addon_compatibility_warning(Operator):
    bl_idname = "vrm.show_blend_file_addon_compatibility_warning"
    bl_label = "VRM Add-on Compatibility Warning"
    bl_description = "Show blend file and VRM add-on compatibility warning."
    bl_options: AbstractSet[str] = {"REGISTER"}

    file_addon_version: StringProperty(options={"HIDDEN"})  # type: ignore[valid-type]
    installed_addon_version: StringProperty(options={"HIDDEN"})  # type: ignore[valid-type]

    def execute(self, _context: Context) -> set[str]:
        return {"FINISHED"}

    def invoke(self, context: Context, _event: Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, _context: Context) -> None:
        column = self.layout.row(align=True).column()
        text = pgettext(
            "The current file is not compatible with the installed VRM Add-on.\n"
            + "The current file was created in VRM Add-on {file_addon_version}, but the"
            + " installed\n"
            + "VRM Add-on version is {installed_addon_version}. This incompatibility\n"
            + "may result in data loss or corruption."
        ).format(
            file_addon_version=self.file_addon_version,
            installed_addon_version=self.installed_addon_version,
        )
        description_outer_column = column.column()
        description_outer_column.emboss = "NONE"
        description_column = description_outer_column.box().column(align=True)
        for i, line in enumerate(text.splitlines()):
            icon = "ERROR" if i == 0 else "NONE"
            description_column.label(text=line, translate=False, icon=icon)

    if TYPE_CHECKING:
        # This code is auto generated.
        # To regenerate, run the `uv run tools/property_typing.py` command.
        file_addon_version: str  # type: ignore[no-redef]
        installed_addon_version: str  # type: ignore[no-redef]


__Operator = TypeVar("__Operator", bound=Operator)


def layout_operator(
    layout: UILayout,
    operator_type: type[__Operator],
    *,
    text: Optional[str] = None,
    text_ctxt: str = "",
    translate: bool = True,
    icon: str = "NONE",
    emboss: bool = True,
    depress: bool = False,
    icon_value: int = 0,
) -> __Operator:
    if text is None:
        text = operator_type.bl_label
    operator = layout.operator(
        operator_type.bl_idname,
        text=text,
        text_ctxt=text_ctxt,
        translate=translate,
        icon=icon,
        emboss=emboss,
        depress=depress,
        icon_value=icon_value,
    )

    split = operator_type.bl_idname.split(".")
    if len(split) != 2:
        message = f"Unexpected bl_idname: {operator_type.bl_idname}"
        raise AssertionError(message)
    name = f"{split[0].encode().upper().decode()}_OT_{split[1]}"
    if type(operator).__qualname__ != name:
        raise AssertionError(
            f"{type(operator)} is not compatible with {operator_type}."
            + f"the expected name is {name}"
        )
    return cast("__Operator", operator)


class VRM_OT_make_estimated_humanoid_t_pose(Operator):
    bl_idname = "vrm.make_estimated_humanoid_t_pose"
    bl_label = "Make Estimated T-Pose"
    bl_description = "Create VRM estimated humanoid T-pose."
    bl_options: AbstractSet[str] = {"REGISTER", "UNDO"}

    armature_object_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
    )

    def update_armature_name(self, _context: Context) -> None:
        message = (
            f"`{type(self).__qualname__}.armature_name` is deprecated"
            + " and will be removed in the next major release."
            + f" `Please use {type(self).__qualname__}.armature_object_name` instead."
        )
        logger.warning(message)
        warnings.warn(message, DeprecationWarning, stacklevel=5)

    armature_name: StringProperty(  # type: ignore[valid-type]
        options={"HIDDEN"},
        update=update_armature_name,
    )
    """`armature_name` is deprecated and will be removed in the next major release.
    Please use `armature_object_name` instead.
    """

    def execute(self, context: Context) -> set[str]:
        if not self.armature_object_name and self.armature_name:
            self.armature_object_name = self.armature_name
        armature = context.blend_data.objects.get(self.armature_object_name)
        if armature is None or armature.type != "ARMATURE":
            return {"CANCELLED"}
        if not set_estimated_humanoid_t_pose(context, armature):
            return {"CANCELLED"}
        return {"FINISHED"}

    if TYPE_CHECKING:
        # This code is auto generated.
        # To regenerate, run the `uv run tools/property_typing.py` command.
        armature_object_name: str  # type: ignore[no-redef]
        armature_name: str  # type: ignore[no-redef]
