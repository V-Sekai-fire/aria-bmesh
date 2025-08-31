# SPDX-License-Identifier: MIT OR GPL-3.0-or-later
import math
from collections.abc import Sequence
from unittest import main

import bpy
from bpy.types import Armature
from mathutils import Euler, Quaternion, Vector

from io_scene_vrm.common import ops, version
from io_scene_vrm.common.test_helper import AddonTestCase
from io_scene_vrm.editor.extension import (
    VrmAddonArmatureExtensionPropertyGroup,
    get_armature_extension,
)

addon_version = version.get_addon_version()
spec_version = VrmAddonArmatureExtensionPropertyGroup.SPEC_VERSION_VRM1


def assert_vector3_equals(
    expected: Vector, actual: Sequence[float], message: str
) -> None:
    if len(actual) != 3:
        message = f"actual length is not 3: {actual}"
        raise AssertionError(message)

    threshold = 0.0001
    if abs(expected[0] - actual[0]) > threshold:
        message = f"{message}: {tuple(expected)} is different from {tuple(actual)}"
        raise AssertionError(message)
    if abs(expected[1] - actual[1]) > threshold:
        message = f"{message}: {tuple(expected)} is different from {tuple(actual)}"
        raise AssertionError(message)
    if abs(expected[2] - actual[2]) > threshold:
        message = f"{message}: {tuple(expected)} is different from {tuple(actual)}"
        raise AssertionError(message)


class TestSpringBone1(AddonTestCase):
    def test_one_joint_extending_in_y_direction(self) -> None:
        context = bpy.context

        bpy.ops.object.add(type="ARMATURE", location=(0, 0, 0))
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        root_bone = armature.data.edit_bones.new("root")
        root_bone.head = Vector((0, 0, 0))
        root_bone.tail = Vector((0, 1, 0))

        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.parent = root_bone
        joint_bone0.head = Vector((0, 1, 0))
        joint_bone0.tail = Vector((0, 2, 0))

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((0, 2, 0))
        joint_bone1.tail = Vector((0, 3, 0))
        bpy.ops.object.mode_set(mode="OBJECT")

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        joints = get_armature_extension(armature.data).spring_bone1.springs[0].joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 1
        joints[0].drag_force = 1
        joints[0].stiffness = 0
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 1
        joints[1].drag_force = 1
        joints[1].stiffness = 0

        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "Initial state joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 2, 0), "Initial state joint1"
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 1 second joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1.7071, -0.7071),
            "After 1 second joint1",
        )

        ops.vrm.update_spring_bone1_animation(delta_time=10000)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 10000 seconds joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 1, -1), "After 10000 seconds joint1"
        )

    def test_one_joint_extending_in_y_direction_with_rotating_armature(self) -> None:
        context = bpy.context

        bpy.ops.object.add(
            type="ARMATURE", location=(1, 0, 0), rotation=(0, 0, math.pi / 2)
        )
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        root_bone = armature.data.edit_bones.new("root")
        root_bone.head = Vector((0, 0, 0))
        root_bone.tail = Vector((0, 0.1, 0))

        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.parent = root_bone
        joint_bone0.head = Vector((0, 1, 0))
        joint_bone0.tail = Vector((0, 1.1, 0))

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((0, 2, 0))
        joint_bone1.tail = Vector((0, 2.1, 0))
        bpy.ops.object.mode_set(mode="OBJECT")

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        joints = get_armature_extension(armature.data).spring_bone1.springs[0].joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 1
        joints[0].drag_force = 1
        joints[0].stiffness = 0
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 1
        joints[1].drag_force = 1
        joints[1].stiffness = 0

        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "Initial state joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 2, 0), "Initial state joint1"
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 1 second joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1.7071, -0.7071),
            "After 1 second joint1",
        )

        ops.vrm.update_spring_bone1_animation(delta_time=100000)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 100000 seconds joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1, -1),
            "After 100000 seconds joint1",
        )

    def test_one_joint_extending_in_y_direction_with_rotating_armature_stiffness(
        self,
    ) -> None:
        context = bpy.context

        bpy.ops.object.add(
            type="ARMATURE", location=(1, 0, 0), rotation=(0, 0, math.pi / 2)
        )
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        root_bone = armature.data.edit_bones.new("root")
        root_bone.head = Vector((0, 0, 0))
        root_bone.tail = Vector((0, 0.8, 0))

        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.parent = root_bone
        joint_bone0.head = Vector((0, 1, 0))
        joint_bone0.tail = Vector((0, 1.8, 0))

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((0, 2, 0))
        joint_bone1.tail = Vector((0, 2.8, 0))
        bpy.ops.object.mode_set(mode="OBJECT")
        armature.pose.bones["joint0"].rotation_mode = "QUATERNION"
        armature.pose.bones["joint0"].rotation_quaternion = Quaternion(
            (1, 0, 0), math.radians(-90)
        )

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        joints = get_armature_extension(armature.data).spring_bone1.springs[0].joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 0
        joints[0].drag_force = 1
        joints[0].stiffness = 1
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 0
        joints[1].drag_force = 1
        joints[1].stiffness = 1

        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "Initial state joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 1, -1), "Initial state joint1"
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 1 second joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1.7071, -0.7071),
            "After 1 second joint1",
        )

        ops.vrm.update_spring_bone1_animation(delta_time=100000)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 100000 seconds joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 2, 0), "After 100000 seconds joint1"
        )

    def test_two_joints_extending_in_y_direction(self) -> None:
        context = bpy.context

        bpy.ops.object.add(type="ARMATURE", location=(0, 0, 0))
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        root_bone = armature.data.edit_bones.new("root")
        root_bone.head = Vector((0, 0, 0))
        root_bone.tail = Vector((0, 0.1, 0))

        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.parent = root_bone
        joint_bone0.head = Vector((0, 1, 0))
        joint_bone0.tail = Vector((0, 1.1, 0))

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((0, 2, 0))
        joint_bone1.tail = Vector((0, 2.1, 0))

        joint_bone2 = armature.data.edit_bones.new("joint2")
        joint_bone2.parent = joint_bone1
        joint_bone2.head = Vector((0, 3, 0))
        joint_bone2.tail = Vector((0, 3.1, 0))
        bpy.ops.object.mode_set(mode="OBJECT")

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        joints = get_armature_extension(armature.data).spring_bone1.springs[0].joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 1
        joints[0].drag_force = 1
        joints[0].stiffness = 0
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 1
        joints[1].drag_force = 1
        joints[1].stiffness = 0
        joints[2].node.bone_name = "joint2"
        joints[2].gravity_power = 1
        joints[2].drag_force = 1
        joints[2].stiffness = 0

        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "Initial state joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 2, 0), "Initial state joint1"
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head, (0, 3, 0), "Initial state joint2"
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 1 second joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1.7071, -0.7071),
            "After 1 second joint1",
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head,
            (0, 2.6824, -0.9280),
            "After 1 second joint2",
        )

        ops.vrm.update_spring_bone1_animation(delta_time=100000)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 100000 seconds joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1, -1),
            "After 100000 seconds joint1",
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head,
            (0, 1, -2),
            "After 100000 seconds joint2",
        )

    def test_two_joints_extending_in_y_direction_roll(self) -> None:
        context = bpy.context

        bpy.ops.object.add(type="ARMATURE", location=(0, 0, 0))
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        root_bone = armature.data.edit_bones.new("root")
        root_bone.head = Vector((0, 0, 0))
        root_bone.tail = Vector((0, 0.1, 0))
        root_bone.roll = math.radians(90)

        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.parent = root_bone
        joint_bone0.head = Vector((0, 1, 0))
        joint_bone0.tail = Vector((0, 1.1, 0))
        joint_bone0.roll = math.radians(45)

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((0, 2, 0))
        joint_bone1.tail = Vector((0, 2.1, 0))
        joint_bone1.roll = math.radians(45)

        joint_bone2 = armature.data.edit_bones.new("joint2")
        joint_bone2.parent = joint_bone1
        joint_bone2.head = Vector((0, 3, 0))
        joint_bone2.tail = Vector((0, 3.1, 0))
        bpy.ops.object.mode_set(mode="OBJECT")

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        joints = get_armature_extension(armature.data).spring_bone1.springs[0].joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 1
        joints[0].drag_force = 1
        joints[0].stiffness = 0
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 1
        joints[1].drag_force = 1
        joints[1].stiffness = 0
        joints[2].node.bone_name = "joint2"
        joints[2].gravity_power = 1
        joints[2].drag_force = 1
        joints[2].stiffness = 0

        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "Initial state joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 2, 0), "Initial state joint1"
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head, (0, 3, 0), "Initial state joint2"
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 1 second joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1.7071, -0.7071),
            "After 1 second joint1",
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head,
            (0, 2.6824, -0.9280),
            "After 1 second joint2",
        )

        ops.vrm.update_spring_bone1_animation(delta_time=100000)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 100000 seconds joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1, -1),
            "After 100000 seconds joint1",
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head,
            (0, 1, -2),
            "After 100000 seconds joint2",
        )

    def test_two_joints_extending_in_y_direction_local_translation(self) -> None:
        context = bpy.context

        bpy.ops.object.add(type="ARMATURE", location=(0, 0, 0))
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        root_bone = armature.data.edit_bones.new("root")
        root_bone.head = Vector((0, 0, 0))
        root_bone.tail = Vector((0, 0.1, 0))
        root_bone.use_local_location = True

        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.parent = root_bone
        joint_bone0.head = Vector((0, 1, 0))
        joint_bone0.tail = Vector((0, 1.1, 0))
        joint_bone0.use_local_location = True

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((0, 2, 0))
        joint_bone1.tail = Vector((0, 2.1, 0))
        joint_bone1.use_local_location = True

        joint_bone2 = armature.data.edit_bones.new("joint2")
        joint_bone2.parent = joint_bone1
        joint_bone2.head = Vector((0, 3, 0))
        joint_bone2.tail = Vector((0, 3.1, 0))
        joint_bone2.use_local_location = False
        bpy.ops.object.mode_set(mode="OBJECT")

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        joints = get_armature_extension(armature.data).spring_bone1.springs[0].joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 1
        joints[0].drag_force = 1
        joints[0].stiffness = 0
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 1
        joints[1].drag_force = 1
        joints[1].stiffness = 0
        joints[2].node.bone_name = "joint2"
        joints[2].gravity_power = 1
        joints[2].drag_force = 1
        joints[2].stiffness = 0

        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "Initial state joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 2, 0), "Initial state joint1"
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head, (0, 3, 0), "Initial state joint2"
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 1 second joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1.7071, -0.7071),
            "After 1 second joint1",
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head,
            (0, 2.6824, -0.9280),
            "After 1 second joint2",
        )

        ops.vrm.update_spring_bone1_animation(delta_time=100000)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 100000 seconds joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1, -1),
            "After 100000 seconds joint1",
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head,
            (0, 1, -2),
            "After 100000 seconds joint2",
        )

    def test_two_joints_extending_in_y_direction_connected(self) -> None:
        context = bpy.context

        bpy.ops.object.add(type="ARMATURE", location=(0, 0, 0))
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        root_bone = armature.data.edit_bones.new("root")
        root_bone.head = Vector((0, 0, 0))
        root_bone.tail = Vector((0, 1, 0))

        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.parent = root_bone
        joint_bone0.head = Vector((0, 1, 0))
        joint_bone0.tail = Vector((0, 2, 0))

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((0, 2, 0))
        joint_bone1.tail = Vector((0, 3, 0))

        joint_bone2 = armature.data.edit_bones.new("joint2")
        joint_bone2.parent = joint_bone1
        joint_bone2.head = Vector((0, 3, 0))
        joint_bone2.tail = Vector((0, 4, 0))

        joint_bone0.use_connect = True
        joint_bone1.use_connect = True
        joint_bone2.use_connect = True
        bpy.ops.object.mode_set(mode="OBJECT")

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        joints = get_armature_extension(armature.data).spring_bone1.springs[0].joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 1
        joints[0].drag_force = 1
        joints[0].stiffness = 0
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 1
        joints[1].drag_force = 1
        joints[1].stiffness = 0
        joints[2].node.bone_name = "joint2"
        joints[2].gravity_power = 1
        joints[2].drag_force = 1
        joints[2].stiffness = 0

        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "Initial state joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 2, 0), "Initial state joint1"
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head, (0, 3, 0), "Initial state joint2"
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 1 second joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1.7071, -0.7071),
            "After 1 second joint1",
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head,
            (0, 2.6824, -0.9280),
            "After 1 second joint2",
        )

        ops.vrm.update_spring_bone1_animation(delta_time=100000)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 100000 seconds joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1, -1),
            "After 100000 seconds joint1",
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head,
            (0, 1, -2),
            "After 100000 seconds joint2",
        )

    def test_one_joint_extending_in_y_direction_gravity_y_object_move_to_z(
        self,
    ) -> None:
        context = bpy.context

        bpy.ops.object.add(type="ARMATURE", location=(0, 0, 0))
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        root_bone = armature.data.edit_bones.new("root")
        root_bone.head = Vector((0, 0, 0))
        root_bone.tail = Vector((0, 1, 0))

        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.parent = root_bone
        joint_bone0.head = Vector((0, 1, 0))
        joint_bone0.tail = Vector((0, 2, 0))

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((0, 2, 0))
        joint_bone1.tail = Vector((0, 3, 0))
        bpy.ops.object.mode_set(mode="OBJECT")

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        joints = get_armature_extension(armature.data).spring_bone1.springs[0].joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 1
        joints[0].gravity_dir = (0, 1, 0)
        joints[0].drag_force = 0
        joints[0].stiffness = 0
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 1
        joints[1].gravity_dir = (0, 1, 0)
        joints[1].drag_force = 0
        joints[1].stiffness = 0

        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "Initial state joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 2, 0), "Initial state joint1"
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 1 second joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 2, 0), "After 1 second joint1"
        )

        armature.location = Vector((0, 0, 1))
        context.view_layer.update()
        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 2 seconds joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1.8944271802, -0.4472135901),
            "After 2 seconds joint1",
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1000000)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head,
            (0, 1, 0),
            "After 1000000 seconds joint0",
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 2, 0),
            "After 1000000 seconds joint1",
        )

    def test_one_joint_extending_in_y_direction_rounding_180_degree(self) -> None:
        context = bpy.context

        bpy.ops.object.add(type="ARMATURE", location=(0, 0, 0))
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        root_bone = armature.data.edit_bones.new("root")
        root_bone.head = Vector((0, 0, 0))
        root_bone.tail = Vector((0, 1, 0))

        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.parent = root_bone
        joint_bone0.head = Vector((0, 1, 0))
        joint_bone0.tail = Vector((0, 2, 0))

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((0, 2, 0))
        joint_bone1.tail = Vector((0, 3, 0))
        bpy.ops.object.mode_set(mode="OBJECT")

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        joints = get_armature_extension(armature.data).spring_bone1.springs[0].joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 1  # First apply gravity to gain momentum
        joints[0].drag_force = 0
        joints[0].stiffness = 0
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 0
        joints[1].drag_force = 0
        joints[1].stiffness = 0

        armature.pose.bones["joint0"].rotation_mode = "QUATERNION"
        armature.pose.bones["joint0"].rotation_quaternion.rotate(Euler((0, math.pi, 0)))

        context.view_layer.update()

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 1, 0), "After 1 second joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1.7071, -0.7071),
            "After 1 second joint1",
        )

    def test_two_joints_extending_in_y_direction_root_down(self) -> None:
        context = bpy.context

        bpy.ops.object.add(type="ARMATURE", location=(0, 0, 0))
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        root_bone = armature.data.edit_bones.new("root")
        root_bone.head = Vector((0, 0, 0))
        root_bone.tail = Vector((0, 0.8, 0))

        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.parent = root_bone
        joint_bone0.head = Vector((0, 1, 0))
        joint_bone0.tail = Vector((0, 1.8, 0))

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((0, 2, 0))
        joint_bone1.tail = Vector((0, 2.8, 0))

        joint_bone2 = armature.data.edit_bones.new("joint2")
        joint_bone2.parent = joint_bone1
        joint_bone2.head = Vector((0, 3, 0))
        joint_bone2.tail = Vector((0, 3.8, 0))
        bpy.ops.object.mode_set(mode="OBJECT")

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        joints = get_armature_extension(armature.data).spring_bone1.springs[0].joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 1
        joints[0].drag_force = 1
        joints[0].stiffness = 0
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 1
        joints[1].drag_force = 1
        joints[1].stiffness = 0
        joints[2].node.bone_name = "joint2"
        joints[2].gravity_power = 1
        joints[2].drag_force = 1
        joints[2].stiffness = 0

        root_pose_bone = armature.pose.bones["root"]
        if root_pose_bone.rotation_mode != "QUATERNION":
            root_pose_bone.rotation_mode = "QUATERNION"
        root_pose_bone.rotation_quaternion = Quaternion((1, 0, 0), math.radians(-90.0))

        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 0, -1), "Initial state joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 0, -2), "Initial state joint1"
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head, (0, 0, -3), "Initial state joint2"
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 0, -1), "After 1 second joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 0, -2),
            "After 1 second joint1",
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head,
            (0, 0, -3),
            "After 1 second joint2",
        )

    def test_two_joints_extending_in_y_direction_with_child_stiffness(self) -> None:
        context = bpy.context

        bpy.ops.object.add(type="ARMATURE")
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        root_bone = armature.data.edit_bones.new("root")
        root_bone.head = Vector((0, 0, 0))
        root_bone.tail = Vector((0, 0.8, 0))

        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.parent = root_bone
        joint_bone0.head = Vector((0, 1, 0))
        joint_bone0.tail = Vector((0, 1.8, 0))

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((0, 2, 0))
        joint_bone1.tail = Vector((0, 2.8, 0))

        joint_bone2 = armature.data.edit_bones.new("joint2")
        joint_bone2.parent = joint_bone1
        joint_bone2.head = Vector((0, 3, 0))
        joint_bone2.tail = Vector((0, 3.8, 0))
        bpy.ops.object.mode_set(mode="OBJECT")

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        joints = get_armature_extension(armature.data).spring_bone1.springs[0].joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 0
        joints[0].drag_force = 1
        joints[0].stiffness = 0
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 0
        joints[1].drag_force = 1
        joints[1].stiffness = 1
        joints[2].node.bone_name = "joint2"
        joints[2].gravity_power = 0
        joints[2].drag_force = 1
        joints[2].stiffness = 0

        armature.pose.bones["joint0"].rotation_mode = "QUATERNION"
        armature.pose.bones["joint0"].rotation_quaternion = Quaternion(
            (1, 0, 0), math.radians(90)
        )

        armature.pose.bones["joint1"].rotation_mode = "QUATERNION"
        armature.pose.bones["joint1"].rotation_quaternion = Quaternion(
            (1, 0, 0), math.radians(90)
        )

        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head,
            (0, 1, 0),
            "Initial state joint0",
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1, 1),
            "Initial state joint1",
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head,
            (0, 0, 1),
            "Initial state joint2",
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head,
            (0, 1, 0),
            "After 1 second joint0",
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1, 1),
            "After 1 second joint1",
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head,
            (0, 0.2929, 1.7071),
            "After 1 second joint2",
        )

        ops.vrm.update_spring_bone1_animation(delta_time=100000)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head,
            (0, 1, 0),
            "After 100000 seconds joint0",
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (0, 1, 1),
            "After 100000 seconds joint1",
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head,
            (0, 1, 2),
            "After 100000 seconds joint2",
        )

    def test_one_joint_extending_in_y_direction_with_roll_stiffness(self) -> None:
        context = bpy.context

        bpy.ops.object.add(type="ARMATURE")
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        root_bone = armature.data.edit_bones.new("root")
        root_bone.head = Vector((0, 0, 0))
        root_bone.tail = Vector((-0.8, 0, 0))

        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.parent = root_bone
        joint_bone0.head = Vector((-1, 0, 0))
        joint_bone0.tail = Vector((-1, 0, -1))
        joint_bone0.roll = math.radians(90)

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((-1, 0, -1))
        joint_bone1.tail = Vector((-1, 0, -2))
        bpy.ops.object.mode_set(mode="OBJECT")

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        joints = get_armature_extension(armature.data).spring_bone1.springs[0].joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 0
        joints[0].drag_force = 1
        joints[0].stiffness = 1
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 0
        joints[1].drag_force = 1
        joints[1].stiffness = 1

        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head,
            (-1, 0, 0),
            "Initial state joint0",
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (-1, 0, -1),
            "Initial state joint1",
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head,
            (-1, 0, 0),
            "After 1 second joint0",
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head,
            (-1, 0, -1),
            "After 1 second joint1",
        )

    def test_two_joints_extending_in_y_direction_center_move_to_z(self) -> None:
        context = bpy.context

        bpy.ops.object.add(type="ARMATURE")
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.head = Vector((0, 0, 0))
        joint_bone0.tail = Vector((0, 0.8, 0))

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((0, 1, 0))
        joint_bone1.tail = Vector((0, 1.8, 0))

        joint_bone2 = armature.data.edit_bones.new("joint2")
        joint_bone2.parent = joint_bone1
        joint_bone2.head = Vector((0, 2, 0))
        joint_bone2.tail = Vector((0, 2.001, 0))
        bpy.ops.object.mode_set(mode="OBJECT")

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        spring = get_armature_extension(armature.data).spring_bone1.springs[0]
        spring.center.bone_name = "joint0"
        joints = spring.joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 0
        joints[0].drag_force = 1
        joints[0].stiffness = 0
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 0
        joints[1].drag_force = 1
        joints[1].stiffness = 0
        joints[2].node.bone_name = "joint2"
        joints[2].gravity_power = 0
        joints[2].drag_force = 1
        joints[2].stiffness = 0

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        armature.location = Vector((0, 0, 1))

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 0, 0), "After 1 second joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 1, 0), "After 1 second joint1"
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head, (0, 2, 0), "After 1 second joint2"
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 0, 0), "After 2 seconds joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 1, 0), "After 2 seconds joint1"
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head, (0, 2, 0), "After 2 seconds joint2"
        )

    def test_two_joints_extending_in_y_direction_center_move_to_z_no_inertia(
        self,
    ) -> None:
        context = bpy.context

        bpy.ops.object.add(type="ARMATURE")
        armature = context.object
        if not armature or not isinstance(armature.data, Armature):
            raise AssertionError

        get_armature_extension(armature.data).addon_version = addon_version
        get_armature_extension(armature.data).spec_version = spec_version
        get_armature_extension(armature.data).spring_bone1.enable_animation = True

        bpy.ops.object.mode_set(mode="EDIT")
        joint_bone0 = armature.data.edit_bones.new("joint0")
        joint_bone0.head = Vector((0, 0, 0))
        joint_bone0.tail = Vector((0, 0.8, 0))

        joint_bone1 = armature.data.edit_bones.new("joint1")
        joint_bone1.parent = joint_bone0
        joint_bone1.head = Vector((0, 1, 0))
        joint_bone1.tail = Vector((0, 1.8, 0))

        joint_bone2 = armature.data.edit_bones.new("joint2")
        joint_bone2.parent = joint_bone1
        joint_bone2.head = Vector((0, 2, 0))
        joint_bone2.tail = Vector((0, 2.001, 0))
        bpy.ops.object.mode_set(mode="OBJECT")

        self.assertEqual(
            ops.vrm.add_spring_bone1_spring(armature_object_name=armature.name),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )
        self.assertEqual(
            ops.vrm.add_spring_bone1_spring_joint(
                armature_object_name=armature.name, spring_index=0
            ),
            {"FINISHED"},
        )

        spring = get_armature_extension(armature.data).spring_bone1.springs[0]
        spring.center.bone_name = "joint0"
        joints = spring.joints
        joints[0].node.bone_name = "joint0"
        joints[0].gravity_power = 0
        joints[0].drag_force = 1
        joints[0].stiffness = 0
        joints[1].node.bone_name = "joint1"
        joints[1].gravity_power = 0
        joints[1].drag_force = 1
        joints[1].stiffness = 0
        joints[2].node.bone_name = "joint2"
        joints[2].gravity_power = 0
        joints[2].drag_force = 1
        joints[2].stiffness = 0

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        armature.location = Vector((0, 0, 1))

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 0, 0), "After 1 second joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 1, 0), "After 1 second joint1"
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head, (0, 2, 0), "After 1 second joint2"
        )

        ops.vrm.update_spring_bone1_animation(delta_time=1)
        context.view_layer.update()

        assert_vector3_equals(
            armature.pose.bones["joint0"].head, (0, 0, 0), "After 2 seconds joint0"
        )
        assert_vector3_equals(
            armature.pose.bones["joint1"].head, (0, 1, 0), "After 2 seconds joint1"
        )
        assert_vector3_equals(
            armature.pose.bones["joint2"].head, (0, 2, 0), "After 2 seconds joint2"
        )


if __name__ == "__main__":
    main()
