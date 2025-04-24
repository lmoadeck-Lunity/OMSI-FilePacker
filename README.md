# OMSI-FilePacker

Packs scenery objects, splines, and their corresponding textures and models from a provided list.

- **Credit**  
  [Thomas Mathieson and his Blender o3d Plugin](https://github.com/space928/Blender-O3D-IO-Public)

Instructions:

1. Place the script in the root folder of your OMSI installation, e.g., `X:\OMSI 2 Steam Edition` or `X:\SteamLibrary\steamapps\common\OMSI 2`.
2. Add the filenames of the scenery objects and splines you want to pack into a text file called `file_paths.txt` (the name can be changed inside the script).
3. Run the script.
4. You will receive a ZIP file and a `did not find.txt` file listing any missing files.

Below is an example of file_paths.txt content:

```txt
Sceneryobjects\3dtranstudio\hkstreet\ped_1_5_end_a.sco
Sceneryobjects\3dtranstudio\hkstreet\ped_1_5_end_b.sco
Splines\47x city\surface mark\str11.sli
Splines\Splines\296d\3str_2spur_8m_ll_line_bridge_concrete_oneway.sli
Splines\Splines\Splines\taxidriverhk_nopaths\2lanes_noped_verywide.sli
Sceneryobjects\Map E31\*
