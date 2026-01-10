import bpy

# Clear default objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import GLB
bpy.ops.import_scene.gltf(filepath='D:/ANYWAVEREPO/animation-studio/characters-reference/3d_output/kyur-3d.glb')

# Select imported objects
for obj in bpy.context.scene.objects:
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    # Scale up 5x for better visibility
    obj.scale = (5, 5, 5)

# Frame all in 3D view
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for region in area.regions:
            if region.type == 'WINDOW':
                override = {'area': area, 'region': region}
                bpy.ops.view3d.view_all(override)
                break

print("=" * 40)
print("Import complete! Objects in scene:")
for obj in bpy.context.scene.objects:
    print(f"  - {obj.name} ({obj.type})")
print("=" * 40)
