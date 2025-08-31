# SPDX-License-Identifier: MIT OR GPL-3.0-or-later
import cProfile
from pstats import SortKey, Stats

import bpy
from bpy.types import Context

from io_scene_vrm.common import version
from io_scene_vrm.common.scene_watcher import (
    RunState,
    SceneWatcher,
    create_fast_path_performance_test_scene,
)
from io_scene_vrm.editor.extension import (
    VrmAddonArmatureExtensionPropertyGroup,
)
from io_scene_vrm.editor.mtoon1.scene_watcher import OutlineUpdater

addon_version = version.get_addon_version()
spec_version = VrmAddonArmatureExtensionPropertyGroup.SPEC_VERSION_VRM1


def run_and_reset_scene_watcher(scene_watcher: SceneWatcher, context: Context) -> None:
    if scene_watcher.run(context) == RunState.FINISH:
        scene_watcher.reset_run_progress()


def benchmark_outline_updater(context: Context) -> None:
    bpy.ops.preferences.addon_enable(module="io_scene_vrm")

    scene_watcher = OutlineUpdater()
    create_fast_path_performance_test_scene(context, scene_watcher)
    # Initial execution can take longer
    run_and_reset_scene_watcher(scene_watcher, context)

    profiler = cProfile.Profile()
    with profiler:
        for _ in range(50000):
            run_and_reset_scene_watcher(scene_watcher, context)

    Stats(profiler).sort_stats(SortKey.TIME).print_stats(50)


if __name__ == "__main__":
    benchmark_outline_updater(bpy.context)
