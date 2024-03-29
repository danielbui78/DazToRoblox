"""Blender Convert DTU to Roblox Blend

This is a command-line script to import a dtu/fbx intermediate file pair into
Blender and convert it to a format compatible with Godot engine, such as GLB,
GLTF or BLEND. The script will also copy the intermediate files to the Godot
project folder, and re-assign the texture paths to the new location.

- Developed and tested with Blender 3.6.1 (Python 3.10.12)
- Uses modified blender_tools.py module
- Requires Blender 3.6 or later

USAGE: blender.exe --background --python blender_dtu_to_godot.py <fbx file>

EXAMPLE:

    C:/Blender3.6/blender.exe --background --python blender_dtu_to_roblox_blend.py C:/Users/dbui/Documents/DazToGodot/Amelia9YoungAdult/Amelia9YoungAdult.fbx

"""
do_experimental_remove_materials = True


logFilename = "blender_dtu_to_roblox_blend.log"

## Do not modify below
def _print_usage():
    # print("Python version: " + str(sys.version))
    print("\nUSAGE: blender.exe --background --python blender_dtu_to_roblox_blend.py <fbx file>\n")

from pathlib import Path
script_dir = str(Path( __file__ ).parent.absolute())

import sys
import os
import json
import re
import shutil
try:
    import bpy
except:
    print("DEBUG: blender python libraries not detected, continuing for pydoc mode.")

try:
    import blender_tools
    blender_tools.logFilename = logFilename
except:
    sys.path.append(script_dir)
    import blender_tools

def _add_to_log(sMessage):
    print(str(sMessage))
    with open(logFilename, "a") as file:
        file.write(sMessage + "\n")

def _main(argv):
    try:
        line = str(argv[-1])
    except:
        _print_usage()
        return

    try:
        start, stop = re.search("#([0-9]*)\.", line).span(0)
        token_id = int(line[start+1:stop-1])
        print(f"DEBUG: token_id={token_id}")
    except:
        print(f"ERROR: unable to parse token_id from '{line}'")
        token_id = 0

    blender_tools.delete_all_items()
    blender_tools.switch_to_layout_mode()

    fbxPath = line.replace("\\","/").strip()
    if (not os.path.exists(fbxPath)):
        _add_to_log("ERROR: main(): fbx file not found: " + str(fbxPath))
        exit(1)
        return

    # load FBX
    _add_to_log("DEBUG: main(): loading fbx file: " + str(fbxPath))
    blender_tools.import_fbx(fbxPath)
    blender_tools.fix_eyes()
    blender_tools.fix_scalp()

    blender_tools.center_all_viewports()
    jsonPath = fbxPath.replace(".fbx", ".dtu")
    _add_to_log("DEBUG: main(): loading json file: " + str(jsonPath))
    dtu_dict = blender_tools.process_dtu(jsonPath)

    if "Has Animation" in dtu_dict:
        bHasAnimation = dtu_dict["Has Animation"]
        # FUTURE TODO: import and process facial animation
    else:
        bHasAnimation = False


    # clear all animation data
    # Iterate over all objects
    print("DEBUG: main(): clearing animation data")
    for obj in bpy.data.objects:
        # Check if the object has animation data
        if obj.animation_data:
            # Clear all animation data
            obj.animation_data_clear()        


    # move root node to origin
    print("DEBUG: main(): moving root node to origin")
    move_root_node_to_origin()

    daz_generation = dtu_dict["Asset Id"]
    if (bHasAnimation == False):
        # if ("Genesis8" in daz_generation):
        #     blender_tools.apply_tpose_for_g8_g9()
        # elif ("Genesis9" in daz_generation):
        #     blender_tools.apply_tpose_for_g8_g9()
        apply_i_pose()

    # add decimate modifier
    add_decimate_modifier()

    # separate by materials
    separate_by_materials()

    # separate by loose parts
    separate_by_loose_parts()

    # separate by bone influence
    separate_by_bone_influence()

    # prepare destination folder path
    blenderFilePath = fbxPath.replace(".fbx", ".blend")
    intermediate_folder_path = os.path.dirname(fbxPath)

    # remove missing or unused images
    print("DEBUG: deleting missing or unused images...")
    for image in bpy.data.images:
        is_missing = False
        if image.filepath:
            imagePath = bpy.path.abspath(image.filepath)
            if (not os.path.exists(imagePath)):
                is_missing = True

        is_unused = False
        if image.users == 0:
            is_unused = True

        if is_missing or is_unused:
            bpy.data.images.remove(image)

    # cleanup all unused and unlinked data blocks
    print("DEBUG: main(): cleaning up unused data blocks...")
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    # pack all images
    print("DEBUG: main(): packing all images...")
    bpy.ops.file.pack_all()

    # select all objects
    bpy.ops.object.select_all(action="SELECT")
    # set active object
    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]

    # switch to object mode before saving
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.wm.save_as_mainfile(filepath=blenderFilePath)
    
    # export to fbx
    roblox_asset_name = dtu_dict["Asset Name"]
    roblox_output_path = dtu_dict["Output Folder"]
    destinationPath = roblox_output_path.replace("\\","/")
    if (not os.path.exists(destinationPath)):
        os.makedirs(destinationPath)
    fbx_base_name = os.path.basename(fbxPath)
    fbx_output_name = fbx_base_name.replace(".fbx", "_roblox.fbx")
    fbx_output_file_path = os.path.join(destinationPath, fbx_output_name).replace("\\","/")
    _add_to_log("DEBUG: saving Roblox FBX file to destination: " + fbx_output_file_path)
    try:
        bpy.ops.export_scene.fbx(filepath=fbx_output_file_path, 
                                 global_scale = 0.0333,
                                 add_leaf_bones = False,
                                 path_mode = "COPY",
                                 embed_textures = True,
                                 )
        _add_to_log("DEBUG: save completed.")
    except Exception as e:
        _add_to_log("ERROR: unable to save Roblox FBX file: " + fbx_output_file_path)
        _add_to_log("EXCEPTION: " + str(e))


    _add_to_log("DEBUG: main(): completed conversion for: " + str(fbxPath))


def apply_i_pose():
    print("DEBUG: apply_i_pose()")
    # Object Mode
    bpy.ops.object.mode_set(mode="OBJECT")       
    #retrieve armature name
    armature_name = bpy.data.armatures[0].name
    for arm in bpy.data.armatures:
        if "genesis" in arm.name.lower():
            armature_name = arm.name
            print("DEBUG: armature_name=" + armature_name)
            break

    # create a list of objects with armature modifier
    armature_modifier_list = []
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            for mod in obj.modifiers:
                if mod.type == "ARMATURE" and mod.name == armature_name:
                    armature_modifier_list.append([obj, mod])
    print("DEBUG: armature_modifier_list=" + str(armature_modifier_list))

    # apply i-pose
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode="POSE")
            bpy.ops.pose.select_all(action='SELECT')
            bpy.ops.pose.rot_clear()
            bpy.ops.object.mode_set(mode="OBJECT")

    # select all objects
    bpy.ops.object.select_all(action="SELECT")
    # switch to pose mode
    bpy.ops.object.mode_set(mode="POSE")
    # go to frame 0
    bpy.context.scene.frame_set(0)
    # clear all pose transforms
    bpy.ops.pose.transforms_clear()
    # set tpose values for shoulders and hips
    if "LeftUpperArm" in bpy.context.object.pose.bones:
        _add_to_log("DEBUG: applying t-pose rotations...")
        # rotate hip "LowerTorso"
        # bpy.context.object.pose.bones["LowerTorso"].rotation_mode= "XYZ"
        # bpy.context.object.pose.bones["LowerTorso"].rotation_euler[0] = 0.17
        # UpperTorso
        # bpy.context.object.pose.bones["UpperTorso"].rotation_mode= "XYZ"
        # bpy.context.object.pose.bones["UpperTorso"].rotation_euler[0] = -0.17
        # rotate left shoulder 50 degrees along global y
        bpy.context.object.pose.bones["LeftUpperArm"].rotation_mode= "XYZ"
        bpy.context.object.pose.bones["LeftUpperArm"].rotation_euler[2] = -0.6
        bpy.context.object.pose.bones["RightUpperArm"].rotation_mode= "XYZ"
        bpy.context.object.pose.bones["RightUpperArm"].rotation_euler[2] = 0.6
        # elbows
        bpy.context.object.pose.bones["LeftLowerArm"].rotation_mode= "XYZ"
        bpy.context.object.pose.bones["LeftLowerArm"].rotation_euler[0] = 0.115
        bpy.context.object.pose.bones["LeftLowerArm"].rotation_euler[1] = 0.079
        bpy.context.object.pose.bones["RightLowerArm"].rotation_mode= "XYZ"
        bpy.context.object.pose.bones["RightLowerArm"].rotation_euler[0] = 0.115
        bpy.context.object.pose.bones["RightLowerArm"].rotation_euler[1] = -0.079
        # wrists
        bpy.context.object.pose.bones["LeftHand"].rotation_mode= "XYZ"
        bpy.context.object.pose.bones["LeftHand"].rotation_euler[0] = -0.122
        bpy.context.object.pose.bones["LeftHand"].rotation_euler[1] = -0.084
        bpy.context.object.pose.bones["RightHand"].rotation_mode= "XYZ"
        bpy.context.object.pose.bones["RightHand"].rotation_euler[0] = -0.122
        bpy.context.object.pose.bones["RightHand"].rotation_euler[1] = 0.084
        # L and R hips to 5 degrees
        bpy.context.object.pose.bones["LeftUpperLeg"].rotation_mode= "XYZ"
        # bpy.context.object.pose.bones["LeftUpperLeg"].rotation_euler[0] = -0.17
        bpy.context.object.pose.bones["LeftUpperLeg"].rotation_euler[2] = -0.026
        bpy.context.object.pose.bones["RightUpperLeg"].rotation_mode= "XYZ"
        # bpy.context.object.pose.bones["RightUpperLeg"].rotation_euler[0] = -0.17
        bpy.context.object.pose.bones["RightUpperLeg"].rotation_euler[2] = 0.026


    # if shapes are present in mesh, then return without baking t-pose since blender can not apply armature modifier
    for obj, mod in armature_modifier_list:
        if obj.data.shape_keys is not None:
            _add_to_log("DEBUG: shape keys found, skipping t-pose bake for G8/G9...")
            return

    # Object Mode
    bpy.ops.object.mode_set(mode="OBJECT")
    # duplicate and apply armature modifier
    for obj, mod in armature_modifier_list:
        _add_to_log("DEBUG: Duplicating armature modifier: " + obj.name + "." + mod.name)
        # select object
        _add_to_log("DEBUG: Selecting object: " + obj.name)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        num_mods = len(obj.modifiers)
        _add_to_log("DEBUG: num_mods = " + str(num_mods))
        result = bpy.ops.object.modifier_copy(modifier=mod.name)
        _add_to_log("DEBUG: result=" + str(result) + ", mod.name=" + mod.name)
        if len(obj.modifiers) > num_mods:
            new_mod = obj.modifiers[num_mods]
            _add_to_log("DEBUG: Applying armature modifier: " + new_mod.name)
            try:
                result = bpy.ops.object.modifier_apply(modifier=new_mod.name)
            except Exception as e:
                _add_to_log("ERROR: Unable to apply armature modifier: " + str(e))
                _add_to_log("DEBUG: result=" + str(result) + ", mod.name=" + new_mod.name)
                bpy.ops.object.modifier_remove(modifier=new_mod.name)     
                return
            _add_to_log("DEBUG: result=" + str(result) + ", mod.name=" + new_mod.name)
        else:
            _add_to_log("DEBUG: Unable to retrieve duplicate, applying original: " + mod.name)
            result = bpy.ops.object.modifier_apply(modifier=mod.name)
            _add_to_log("DEBUG: result=" + str(result) + ", mod.name=" + mod.name)

    # pose mode
    bpy.ops.object.select_all(action="DESELECT")
    armature_obj = bpy.data.objects.get(armature_name)
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode="POSE")
    # apply pose as rest pose
    _add_to_log("DEBUG: Applying pose as rest pose...")
    bpy.ops.pose.armature_apply(selected=False)
    # Object Mode
    bpy.ops.object.mode_set(mode="OBJECT")
    # select all before returning
    bpy.ops.object.select_all(action="SELECT")

def move_root_node_to_origin():
    print("DEBUG: move_root_node_to_origin(): bpy.data.objects=" + str(bpy.data.objects))
    # move root node to origin
    for obj in bpy.data.objects:
        print("DEBUG: move_root_node_to_origin(): obj.name=" + obj.name + ", obj.type=" + obj.type)
        if obj.type == 'ARMATURE':
            # deselect all objects
            bpy.ops.object.select_all(action='DESELECT')
            # select armature object
            obj.select_set(True)
            # select "LowerTorso" bone
            bpy.context.view_layer.objects.active = obj            
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.context.object.data.bones["LowerTorso"].select = True
            bone_head_pos_y = bpy.context.object.data.bones["LowerTorso"].head.y
            bone_head_pos_z = bpy.context.object.data.bones["LowerTorso"].head.z            
            print("DEBUG: move_root_node_to_origin(): bone_head_pos_y=" + str(bone_head_pos_y) + ", bone_head_pos_z=" + str(bone_head_pos_z))
            bpy.ops.object.mode_set(mode="OBJECT")
            # select all objects in object mode
            bpy.ops.object.select_all(action='SELECT')
            # move all objects by the inverse of bone_head_pos
            inverse_bone_head_pos_z = -0.01 * bone_head_pos_y
            inverse_bone_head_pos_x = -0.01 * bone_head_pos_z
            print("DEBUG: move_root_node_to_origin(): inverse_bone_head_pos_x=" + str(inverse_bone_head_pos_x) + ", inverse_bone_head_pos_z=" + str(inverse_bone_head_pos_z))
            bpy.ops.transform.translate(value=(inverse_bone_head_pos_x, 0, inverse_bone_head_pos_z))
            # apply transformation
            bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)


def add_decimate_modifier():
    # add decimate modifier
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_add(type='DECIMATE')
            bpy.context.object.modifiers["Decimate"].ratio = 0.2

def separate_by_materials():
    # separate by materials
    bpy.ops.object.mode_set(mode="OBJECT")
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.separate(type='MATERIAL')
            bpy.ops.object.mode_set(mode="OBJECT")

    # clean up unwanted materials
    bpy.ops.object.mode_set(mode="OBJECT")
    fingernail_obj = None
    arms_obj = None
    toenails_obj = None
    legs_obj = None
    eyes_list = []
    head_obj = None
    mouth_list = []
    for obj in bpy.data.objects:
        # query for material names of each obj
        if obj.type == 'MESH':
            obj_materials = obj.data.materials
            # if only one material, then rename object to material.name + "_Geo"
            if len(obj_materials) == 1:
                obj.name = obj_materials[0].name.replace(" ","") + "_Geo"
            for mat in obj_materials:
                # if "Tear" in mat.name or "moisture" in mat.name.lower() or "eyebrows" in mat.name.lower() or "eyelashes" in mat.name.lower() or "teeth" in mat.name.lower() or "mouth" in mat.name.lower():
                if "Tear" in mat.name or "moisture" in mat.name.lower() or "eyebrows" in mat.name.lower() or "eyelashes" in mat.name.lower():
                    # remove obj
                    print("DEBUG: Removing object " + obj.name + " with material: " + mat.name)
                    # delete heirarchy of object
                    descendents = obj.children
                    bpy.ops.object.select_all(action='DESELECT')
                    for ob in descendents:
                        ob.select_set(True)
                    bpy.ops.object.delete()
                    obj.select_set(True)
                    bpy.ops.object.delete()
                    break
                if "head" in mat.name.lower():
                    head_obj = obj
                    # get decimation modifier
                    decimate_modifier = None
                    for mod in obj.modifiers:
                        if mod.type == "DECIMATE":
                            decimate_modifier = mod
                            break
                    if decimate_modifier is not None:
                        # change decimate ratio to 0.36
                        decimate_modifier.ratio = 0.36
                        # apply decimate modifier
                        bpy.ops.object.select_all(action='DESELECT')
                        obj.select_set(True)
                        bpy.context.view_layer.objects.active = obj
                        bpy.ops.object.modifier_apply(modifier=decimate_modifier.name)

                if "eye" in mat.name.lower():
                    eyes_list.append(obj)
                    # get decimation modifier
                    decimate_modifier = None
                    for mod in obj.modifiers:
                        if mod.type == "DECIMATE":
                            decimate_modifier = mod
                            break
                    if decimate_modifier is not None:
                        # change decimate ratio to 0.09
                        decimate_modifier.ratio = 0.09
                        # apply decimate modifier
                        bpy.ops.object.select_all(action='DESELECT')
                        obj.select_set(True)
                        bpy.context.view_layer.objects.active = obj
                        bpy.ops.object.modifier_apply(modifier=decimate_modifier.name)
                if "teeth" in mat.name.lower():
                    mouth_list.append(obj)
                    # get decimation modifier
                    decimate_modifier = None
                    for mod in obj.modifiers:
                        if mod.type == "DECIMATE":
                            decimate_modifier = mod
                            break
                    if decimate_modifier is not None:
                        # change decimate ratio to 0.09
                        decimate_modifier.ratio = 0.09
                        # apply decimate modifier
                        bpy.ops.object.select_all(action='DESELECT')
                        obj.select_set(True)
                        bpy.context.view_layer.objects.active = obj
                        bpy.ops.object.modifier_apply(modifier=decimate_modifier.name)
                if "mouth cavity" in mat.name.lower():
                    mouth_list.append(obj)
                    # get decimation modifier
                    decimate_modifier = None
                    for mod in obj.modifiers:
                        if mod.type == "DECIMATE":
                            decimate_modifier = mod
                            break
                    if decimate_modifier is not None:
                        # change decimate ratio to 0.068
                        decimate_modifier.ratio = 0.068
                        # apply decimate modifier
                        bpy.ops.object.select_all(action='DESELECT')
                        obj.select_set(True)
                        bpy.context.view_layer.objects.active = obj
                        bpy.ops.object.modifier_apply(modifier=decimate_modifier.name)
                elif "mouth" in mat.name.lower():
                    mouth_list.append(obj)
                    # get decimation modifier
                    decimate_modifier = None
                    for mod in obj.modifiers:
                        if mod.type == "DECIMATE":
                            decimate_modifier = mod
                            break
                    if decimate_modifier is not None:
                        # change decimate ratio to 0.036
                        decimate_modifier.ratio = 0.036
                        # apply decimate modifier
                        bpy.ops.object.select_all(action='DESELECT')
                        obj.select_set(True)
                        bpy.context.view_layer.objects.active = obj
                        bpy.ops.object.modifier_apply(modifier=decimate_modifier.name)
                
                if "fingernails" in mat.name.lower():
                    fingernail_obj = obj
                if "arms" in mat.name.lower():
                    arms_obj = obj
                if "toenails" in mat.name.lower():
                    toenails_obj = obj
                if "legs" in mat.name.lower():
                    legs_obj = obj
    
    # merge objects
    print("DEBUG: merging objects...")
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = bpy.data.objects[0]
    bpy.ops.object.mode_set(mode="OBJECT")
    if fingernail_obj is not None and arms_obj is not None:
        # deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        arms_obj.select_set(True)
        fingernail_obj.select_set(True)
        bpy.context.view_layer.objects.active = arms_obj
        bpy.ops.object.join()
        if do_experimental_remove_materials:
            bpy.context.view_layer.objects.active = arms_obj
            # remove material named "Fingernails"
            material_name = "Fingernails"
            material_slot = next((slot for slot in arms_obj.material_slots if slot.name == material_name), None)
            # If the material slot exists, remove it
            if material_slot:
                bpy.context.object.active_material_index = arms_obj.material_slots.find(material_name)
                bpy.ops.object.material_slot_remove()

    if toenails_obj is not None and legs_obj is not None:
        # deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        legs_obj.select_set(True)
        toenails_obj.select_set(True)
        bpy.context.view_layer.objects.active = legs_obj
        bpy.ops.object.join()
        if do_experimental_remove_materials:
            bpy.context.view_layer.objects.active = legs_obj
            # remove material named "Toenails"
            material_name = "Toenails"
            material_slot = next((slot for slot in legs_obj.material_slots if slot.name == material_name), None)
            # If the material slot exists, remove it
            if material_slot:
                bpy.context.object.active_material_index = legs_obj.material_slots.find(material_name)
                bpy.ops.object.material_slot_remove()

    if len(eyes_list) > 0 and head_obj is not None:
        # merge eyes
        print("DEBUG: merging eyes...")
        bpy.ops.object.select_all(action='DESELECT')
        head_obj.select_set(True)
        for obj in eyes_list:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = head_obj
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.join()
        if do_experimental_remove_materials:
            bpy.context.view_layer.objects.active = head_obj
            # remove material named "Eye Left" and "Eye Right"
            material_name = "Eye Left"
            material_slot = next((slot for slot in head_obj.material_slots if slot.name == material_name), None)
            # If the material slot exists, remove it
            if material_slot:
                bpy.context.object.active_material_index = head_obj.material_slots.find(material_name)
                bpy.ops.object.material_slot_remove()
            material_name = "Eye Right"
            material_slot = next((slot for slot in head_obj.material_slots if slot.name == material_name), None)
            # If the material slot exists, remove it
            if material_slot:
                bpy.context.object.active_material_index = head_obj.material_slots.find(material_name)
                bpy.ops.object.material_slot_remove()

    if len(mouth_list) > 0 and head_obj is not None:
        # merge mouth, mouth cavity, and teeth
        print("DEBUG: merging mouth, mouth cavity, and teeth...")
        bpy.ops.object.select_all(action='DESELECT')
        head_obj.select_set(True)
        for obj in mouth_list:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = head_obj
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.join()
        if do_experimental_remove_materials:
            bpy.context.view_layer.objects.active = head_obj
            # remove material named "Mouth Cavity" and "Teeth"
            material_name = "Mouth Cavity"
            material_slot = next((slot for slot in head_obj.material_slots if slot.name == material_name), None)
            # If the material slot exists, remove it
            if material_slot:
                bpy.context.object.active_material_index = head_obj.material_slots.find(material_name)
                bpy.ops.object.material_slot_remove()
            material_name = "Teeth"
            material_slot = next((slot for slot in head_obj.material_slots if slot.name == material_name), None)
            # If the material slot exists, remove it
            if material_slot:
                bpy.context.object.active_material_index = head_obj.material_slots.find(material_name)
                bpy.ops.object.material_slot_remove()
            # remove material named "Mouth"
            material_name = "Mouth"
            material_slot = next((slot for slot in head_obj.material_slots if slot.name == material_name), None)
            # If the material slot exists, remove it
            if material_slot:
                bpy.context.object.active_material_index = head_obj.material_slots.find(material_name)
                bpy.ops.object.material_slot_remove()

    print("DEBUG: done separating by materials")

def separate_by_loose_parts():
    print("DEBUG: separate_by_loose_parts()")
    # separate by loose parts
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.separate(type='LOOSE')
            bpy.ops.object.mode_set(mode="OBJECT")

    # clean up loose parts
    right_arm = []
    left_arm = []
    right_leg = []
    left_leg = []
    head_list = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj_materials = obj.data.materials
            for mat in obj_materials:
                if "Head" in mat.name:
                    head_list.append(obj)
                    # break to next obj
                    break
                if "Arms" in mat.name:
                    # check vertices of obj, if x position is less than 0 then collect into right_arm array to merge together
                    for v in obj.data.vertices:
                        if v.co.x > 0:
                            left_arm.append(obj)
                            break
                        else:
                            right_arm.append(obj)
                            break
                    # break to next obj
                    break
                if "Legs" in mat.name:
                    # check vertices of obj, if x position is less than 0 then collect into right_leg array to merge together
                    for v in obj.data.vertices:
                        if v.co.x > 0:
                            left_leg.append(obj)
                            break
                        else:
                            right_leg.append(obj)
                            break
                    # break to next obj
                    break

    # merge right_arm
    print("DEBUG: merging right_arm...")
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = bpy.data.objects[0]
    bpy.ops.object.mode_set(mode="OBJECT")
    if len(right_arm) > 0:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in right_arm:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = right_arm[0]
        bpy.ops.object.join()
        right_arm[0].name = "RightArm_Geo"
    # merge left_arm
    print("DEBUG: merging left_arm...")
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = bpy.data.objects[0]
    bpy.ops.object.mode_set(mode="OBJECT")
    if len(left_arm) > 0:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in left_arm:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = left_arm[0]
        bpy.ops.object.join()
        left_arm[0].name = "LeftArm_Geo"
    # merge right_leg
    print("DEBUG: merging right_leg...")
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = bpy.data.objects[0]
    bpy.ops.object.mode_set(mode="OBJECT")
    if len(right_leg) > 0:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in right_leg:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = right_leg[0]
        bpy.ops.object.join()
        right_leg[0].name = "RightLeg_Geo"
    # merge left_leg
    print("DEBUG: merging left_leg...")
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = bpy.data.objects[0]
    bpy.ops.object.mode_set(mode="OBJECT")
    if len(left_leg) > 0:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in left_leg:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = left_leg[0]
        bpy.ops.object.join()
        left_leg[0].name = "LeftLeg_Geo"

    # merge head
    print("DEBUG: merging head...")
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = bpy.data.objects[0]
    bpy.ops.object.mode_set(mode="OBJECT")
    if len(head_list) > 0:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in head_list:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = head_list[0]
        bpy.ops.object.join()
        head_list[0].name = "Head_Geo"

    print("DEBUG: done separating by loose parts")


def separate_by_bone_influence():
    print("DEBUG: separate_by_bone_influence()")
    # separate by bone influence
    bpy.ops.object.mode_set(mode="OBJECT")
    bone_table = {
        "RightArm_Geo": ["RightHand", "RightLowerArm", "RightUpperArm"],
        "LeftArm_Geo": ["LeftHand", "LeftLowerArm", "LeftUpperArm"],
        "RightLeg_Geo": ["RightFoot", "RightLowerLeg", "RightUpperLeg"],
        "LeftLeg_Geo": ["LeftFoot", "LeftLowerLeg", "LeftUpperLeg"],
        "Body_Geo": ["UpperTorso", "LowerTorso"]
    }
    # deselect all
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name in bone_table:
            bone_list = bone_table[obj.name]
            bpy.context.view_layer.objects.active = obj
            for bone_name in bone_list:
                print("DEBUG: beginning vertex separation for bone_name=" + bone_name)
                bpy.ops.object.mode_set(mode="EDIT")
                # deselect all vertices
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.object.mode_set(mode="OBJECT")
                # get list of all objects before separation operation
                before_list = set(bpy.context.scene.objects)
                # select vertices by bone group
                group = obj.vertex_groups.get(bone_name)
                for v in obj.data.vertices:
                    for g in v.groups:
                        if g.group == group.index:
                            v.select = True                
                bpy.ops.object.mode_set(mode="EDIT")
                # separate by selection
                bpy.ops.mesh.separate(type='SELECTED')
                # rename newly separated object
                # find the new object
                # get list of all objects after separation operation
                after_list = set(bpy.context.scene.objects)
                new_obj = None
                for obj_temp in after_list:
                    if obj_temp not in before_list:
                        new_obj = obj_temp
                        break
                # Switch to object mode
                bpy.ops.object.mode_set(mode='OBJECT')
                # The newly created object is the active object
                if new_obj == obj:
                    print("ERROR: new_obj.name=" + new_obj.name + " is the same as " + obj.name)
                else:
                    # Select the new object
                    print("DEBUG: new_obj.name=" + new_obj.name + " renamed to " + bone_name + "_Geo")
                    new_obj.name = bone_name + "_Geo"
                    # deselect all objects
                    bpy.ops.object.select_all(action='DESELECT')
                    bpy.context.view_layer.objects.active = obj

    # clean up empty objects without vertices
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and len(obj.data.vertices) == 0:
            print("DEBUG: Removing empty object: " + obj.name)
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.ops.object.delete()


def load_and_merge_cage_meshes_from_template_file(template_filepath_blend):
    # load and merge cage meshes from template file
    bpy.ops.wm.append(filename="CageMeshes", directory=template_filepath_blend + "/Object/")
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and "CageMesh" in obj.name:
            obj.select_set(True)
    bpy.ops.object.join()

def load_and_merge_attachments_from_template_file(template_filepath_blend):
    # load and merge attachments from template file
    bpy.ops.wm.append(filename="Attachments", directory=template_filepath_blend + "/Object/")
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and "Attachment" in obj.name:
            obj.select_set(True)
    bpy.ops.object.join()

# Execute main()
if __name__=='__main__':
    print("Starting script...")
    _add_to_log("Starting script... DEBUG: sys.argv=" + str(sys.argv))
    _main(sys.argv[4:])
    print("script completed.")
    exit(0)
