# SPDX-License-Identifier: MIT OR GPL-3.0-or-later
from bpy.types import Armature, Context, UILayout, UIList

from ...common.logger import get_logger
from ..extension import get_armature_extension
from .property_group import (
    SpringBone1ColliderGroupPropertyGroup,
    SpringBone1ColliderGroupReferencePropertyGroup,
    SpringBone1ColliderPropertyGroup,
    SpringBone1ColliderReferencePropertyGroup,
    SpringBone1JointPropertyGroup,
    SpringBone1SpringPropertyGroup,
)

logger = get_logger(__name__)


class VRM_UL_spring_bone1_collider(UIList):
    bl_idname = "VRM_UL_spring_bone1_collider"

    def draw_item(
        self,
        _context: Context,
        layout: UILayout,
        _data: object,
        collider: object,
        _icon: int,
        _active_data: object,
        _active_prop_name: str,
        _index: int,
        _flt_flag: int,
    ) -> None:
        if not isinstance(collider, SpringBone1ColliderPropertyGroup):
            return

        icon = "SPHERE"

        if self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", translate=False, icon=icon)
            return

        if self.layout_type not in {"DEFAULT", "COMPACT"}:
            return

        name = ""
        bpy_object = collider.bpy_object
        if bpy_object:
            name = bpy_object.name
        layout.label(text=name, translate=False, icon=icon)


class VRM_UL_spring_bone1_collider_group(UIList):
    bl_idname = "VRM_UL_spring_bone1_collider_group"

    def draw_item(
        self,
        _context: Context,
        layout: UILayout,
        _data: object,
        collider_group: object,
        _icon: int,
        _active_data: object,
        _active_prop_name: str,
        _index: int,
        _flt_flag: int,
    ) -> None:
        if not isinstance(collider_group, SpringBone1ColliderGroupPropertyGroup):
            return

        icon = "PIVOT_INDIVIDUAL"

        if self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", translate=False, icon=icon)
            return

        if self.layout_type not in {"DEFAULT", "COMPACT"}:
            return

        layout.label(text=collider_group.vrm_name, translate=False, icon=icon)


class VRM_UL_spring_bone1_collider_group_collider(UIList):
    bl_idname = "VRM_UL_spring_bone1_collider_group_collider"

    def draw_item(
        self,
        _context: Context,
        layout: UILayout,
        collider_group: object,
        collider: object,
        _icon: int,
        _active_data: object,
        _active_prop_name: str,
        index: int,
        _flt_flag: int,
    ) -> None:
        if not isinstance(collider_group, SpringBone1ColliderGroupPropertyGroup):
            return
        if not isinstance(collider, SpringBone1ColliderReferencePropertyGroup):
            return
        icon = "SPHERE"

        if self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", translate=False, icon=icon)
            return

        if self.layout_type not in {"DEFAULT", "COMPACT"}:
            return

        armature_data = collider_group.id_data
        if not isinstance(armature_data, Armature):
            logger.error("Failed to find armature")
            return
        spring_bone = get_armature_extension(armature_data).spring_bone1

        if index == collider_group.active_collider_index:
            layout.prop_search(
                collider,
                "collider_name",
                spring_bone,
                "colliders",
                text="",
                translate=False,
                icon=icon,
            )
        else:
            layout.label(text=collider.collider_name, translate=False, icon=icon)


class VRM_UL_spring_bone1_spring(UIList):
    bl_idname = "VRM_UL_spring_bone1_spring"

    def draw_item(
        self,
        _context: Context,
        layout: UILayout,
        _data: object,
        spring: object,
        _icon: int,
        _active_data: object,
        _active_prop_name: str,
        _index: int,
        _flt_flag: int,
    ) -> None:
        if not isinstance(spring, SpringBone1SpringPropertyGroup):
            return

        icon = "PHYSICS"

        if self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", translate=False, icon=icon)
            return

        if self.layout_type not in {"DEFAULT", "COMPACT"}:
            return

        layout.label(text=spring.vrm_name, translate=False, icon=icon)


class VRM_UL_spring_bone1_joint(UIList):
    bl_idname = "VRM_UL_spring_bone1_joint"

    def draw_item(
        self,
        _context: Context,
        layout: UILayout,
        _data: object,
        joint: object,
        _icon: int,
        _active_data: object,
        _active_prop_name: str,
        _index: int,
        _flt_flag: int,
    ) -> None:
        if not isinstance(joint, SpringBone1JointPropertyGroup):
            return

        icon = "BONE_DATA"

        if self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", translate=False, icon=icon)
            return

        if self.layout_type not in {"DEFAULT", "COMPACT"}:
            return

        layout.label(text=joint.node.bone_name, translate=False, icon=icon)


class VRM_UL_spring_bone1_spring_collider_group(UIList):
    bl_idname = "VRM_UL_spring_bone1_spring_collider_group"

    def draw_item(
        self,
        _context: Context,
        layout: UILayout,
        spring: object,
        collider_group: object,
        _icon: int,
        _active_data: object,
        _active_prop_name: str,
        index: int,
        _flt_flag: int,
    ) -> None:
        if not isinstance(spring, SpringBone1SpringPropertyGroup):
            return
        if not isinstance(
            collider_group, SpringBone1ColliderGroupReferencePropertyGroup
        ):
            return

        icon = "PIVOT_INDIVIDUAL"

        if self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", translate=False, icon=icon)
            return

        if self.layout_type not in {"DEFAULT", "COMPACT"}:
            return

        armature_data = spring.id_data
        if not isinstance(armature_data, Armature):
            logger.error("Failed to find armature")
            return
        spring_bone = get_armature_extension(armature_data).spring_bone1

        if index == spring.active_collider_group_index:
            layout.prop_search(
                collider_group,
                "collider_group_name",
                spring_bone,
                "collider_groups",
                text="",
                translate=False,
                icon=icon,
            )
        else:
            layout.label(
                text=collider_group.collider_group_name, translate=False, icon=icon
            )
