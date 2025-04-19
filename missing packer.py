import os
import shutil
import zipfile

# def pack_files(source_dir, output_zip_file, file_paths):
#     temp_dir = os.path.join(source_dir, 'temp')
#     os.makedirs(temp_dir, exist_ok=True)
#     added_files = set()
#     for file_path in file_paths:
#         full_path = os.path.join(source_dir, file_path)
#         dest_path = os.path.join(temp_dir, file_path)
#         os.makedirs(os.path.dirname(dest_path), exist_ok=True)
#         shutil.copy(full_path, dest_path)
#         added_files.add(dest_path)

#         # Include 'model' and 'texture' folders and their contents
#         for folder in ['model', 'texture']:
#             folder_path = os.path.join(os.path.dirname(full_path), folder)
#             if os.path.exists(folder_path):
#                 for root, _, files in os.walk(folder_path):
#                     for file in files:
#                         file_full_path = os.path.join(root, file)
#                         dest_path = os.path.join(temp_dir, os.path.relpath(file_full_path, source_dir))
#                         os.makedirs(os.path.dirname(dest_path), exist_ok=True)
#                         shutil.copy(file_full_path, dest_path)
#                         added_files.add(dest_path)

#     with zipfile.ZipFile(output_zip_file, 'w') as zip_file:
#         for file_path in added_files:
#             zip_file.write(file_path, os.path.relpath(file_path, temp_dir))

#     shutil.rmtree(temp_dir)
import os
import zipfile
import struct


# ==============================================================================
#  Copyright (c) 2022 Thomas Mathieson.
# ==============================================================================




def log(*args):
    print("[O3DConvert]", *args)


def init_rand(encryption_header, alt_encryption_seed, version):
    return 0


def decrypt_vert(vert, encryption_header, alt_encryption_seed, prev_seed, prev_vpos_seed, n_verts):
    return vert, 0, 0


def encrypt_vert(vert, encryption_header, alt_encryption_seed, prev_seed, prev_vpos_seed, n_verts):
    return vert, 0, 0


# Takes an o3d vertex and returns (((pos), (nrm), (uv)), bewOffset)
def import_vertex(buff, offset):
    v = struct.unpack_from("<ffffffff", buff, offset=offset)  # xp,yp,zp,xn,yn,zn,u,v
    return [[list(v[0:3]), list(v[3:6]), list(v[6:8])], offset + 8 * 4]


# Takes an o3d triangle struct and returns ((indices, matIndex), newOffset)
def import_triangle(buff, offset, long_triangle_indices, invert_normals=False):
    if long_triangle_indices:
        t = struct.unpack_from("<IIIH", buff, offset=offset)
        offset += 4 * 3 + 2
    else:
        t = struct.unpack_from("<HHHH", buff, offset=offset)
        offset += 2 * 4

    if invert_normals:
        return (t[0:3], t[3]), offset
    else:
        return (t[0:3][::-1], t[3]), offset


# Takes an o3d material struct and returns:
#      ((diffuse_r, diffuse_g, diffuse_b, diffuse_a),
#       (specular_r, specular_g, specular_b),
#       (emission_r, emission_g, emission_b),
#       specular_power, texture_name)
# is set to None if one isn't specified in the file
def import_material(buff, offset):
    m = struct.unpack_from("<fffffffffffB", buff, offset=offset)
    offset += 11 * 4
    # Extract texture path length
    path_len = m[-1] + 1  # Path length
    m_name = None
    if path_len + 1 > 0:
        try:
            m_name = struct.unpack_from("<{0}p".format(str(path_len)), buff, offset=offset)[0].decode("cp1252")
        except:
            m_name = ""
        offset += path_len
    return (m[0:4], m[4:7], m[7:10], m[10], m_name), offset


# Takes an o3d bone struct and returns ((name, weights), newOffset)
def import_bone(buff, offset, long_triangle_indices):
    h = struct.unpack_from("<B", buff, offset=offset)  # Name length
    b_name = struct.unpack_from("<{0}p".format(str(h[0] + 1)), buff, offset=offset)[0].decode("cp1252",
                                                                                              errors="backslashreplace")
    offset += h[0] + 1

    n_weights = struct.unpack_from("<H", buff, offset=offset)
    offset += 2
    weights = []
    for w in range(n_weights[0]):
        weights.append(struct.unpack_from("<If" if long_triangle_indices else "<Hf", buff, offset=offset))
        offset += 8 if long_triangle_indices else 6

    return (b_name, weights), offset


# Imports a list of o3d vertices and returns (vertices, newOffset)
def import_vertex_list(buff, offset, l_header, encrypted, alt_encryption_seed, encryption_header, version):
    if l_header:
        header = struct.unpack_from("<I", buff, offset=offset)[0]
        offset += 4
    else:
        header = struct.unpack_from("<H", buff, offset=offset)[0]
        offset += 2

    verts = []
    prev_vpos_seed = 0
    prev_seed = init_rand(encryption_header, alt_encryption_seed, version)
    for v in range(header):
        nv = import_vertex(buff, offset)
        if encrypted:
            nv[0], prev_seed, prev_vpos_seed = decrypt_vert(nv[0], encryption_header, alt_encryption_seed, prev_seed,
                                                            prev_vpos_seed, header)

        verts.append(nv[0])
        offset = nv[1]

    return verts, offset


# Imports a list of o3d triangles and returns (triangles, newOffset)
def import_triangle_list(buff, offset, l_header, long_triangle_indices):
    if l_header:
        header = struct.unpack_from("<I", buff, offset=offset)[0]
        offset += 4
    else:
        header = struct.unpack_from("<H", buff, offset=offset)[0]
        offset += 2

    tris = []
    for t in range(header):
        nt = import_triangle(buff, offset, long_triangle_indices, True)
        tris.append(nt[0])
        offset = nt[1]

    return tris, offset


# Imports a list of o3d materials and returns (materials, newOffset)
def import_material_list(buff, offset, l_header):
    # IDK why but materials don't get the long header...
    header = struct.unpack_from("<H", buff, offset=offset)[0]
    offset += 2

    mats = []
    for m in range(header):
        nm = import_material(buff, offset)
        mats.append(nm[0])
        offset = nm[1]

    return mats, offset


# Imports a list of o3d bones and returns (bones, newOffset)
def import_bone_list(buff, offset, l_header, long_triangle_indices):
    if l_header:
        header = struct.unpack_from("<I", buff, offset=offset)[0]
        offset += 4
    else:
        header = struct.unpack_from("<H", buff, offset=offset)[0]
        offset += 2

    bones = []
    for b in range(header):
        nb = import_bone(buff, offset, long_triangle_indices)
        bones.append(nb[0])
        offset = nb[1]

    return bones, offset


# Imports an o3d transform struct and returns (transform, newOffset)
def import_transform(buff, offset):
    m = struct.unpack_from("<ffffffffffffffff", buff, offset=offset)
    offset += 16 * 4
    return (
               (m[0], m[4], m[8], m[12]),
               (m[1], m[5], m[9], m[13]),
               (m[2], m[6], m[10], m[14]),
               (m[3], m[7], m[11], m[15])
           ), offset


def import_o3d(packed_bytes,name):
    header = struct.unpack_from("<BBB", packed_bytes, offset=0)
    off = 3
    l_header = False
    encrypted = False
    bonus_header = [0, 0]
    if header[0:2] == (0x84, 0x19):
        if header[2] > 3:
            # Long header variant, sometimes encrypted
            bonus_header = struct.unpack_from("<BI", packed_bytes, offset=off)
            # log("Extended header options: long_triangle_indices={0}; alt_encryption_seed={1}; encryption_key={2}".format(
            #    bonus_header[0] & 1 == 1, bonus_header[0] & 2 == 2, bonus_header[1]))
            if bonus_header[1] != 0xffffffff:
                encrypted = True
                # log("Encrypted file detected!")
            off += 5
            l_header = True
    else:
        log(
            "WARNING: O3D file has an unsupported header (found={0}; expected=(0x84,0x19,0x01). File might not import "
            "correctly...".format(
                list(map(hex, header))))

    vertex_list = []
    triangle_list = []
    material_list = []
    bone_list = []
    transform = ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))
    while off < len(packed_bytes) - 1:
        section = struct.unpack_from("<B", packed_bytes, offset=off)[0]
        off += 1
        if section == 0x17:
            vertex_list, off = import_vertex_list(packed_bytes, off, l_header, encrypted, bonus_header[0] & 2 == 2,
                                                  bonus_header[1], header[2])
            # log("Loaded {0} vertices!".format(len(vertex_list)))
        elif section == 0x49:
            triangle_list, off = import_triangle_list(packed_bytes, off, l_header, bonus_header[0] & 1 == 1)
            # log("Loaded {0} triangles!".format(len(triangle_list)))
        elif section == 0x26:
            material_list, off = import_material_list(packed_bytes, off, l_header)
            # log("Loaded {0} materials!".format(len(material_list)))
        elif section == 0x54:
            bone_list, off = import_bone_list(packed_bytes, off, l_header, bonus_header[0] & 1 == 1)
            # log("Loaded {0} bones!".format(len(bone_list)))
        elif section == 0x79:
            transform, off = import_transform(packed_bytes, off)
        else:
            log("Unexpected section header encountered in o3d file: " + hex(section) + " at: " + hex(off))
            break

        # triangle_list, off = import_triangle_list(packed_bytes, off, l_header, bonus_header[0])
        # # log("Loaded {0} triangles!".format(len(triangle_list)))
        # material_list, off = import_material_list(packed_bytes, off, l_header)
        # # log("Loaded {0} materials!".format(len(material_list)))
        # bone_list, off = import_bone_list(packed_bytes, off, l_header)
        # # log("Loaded {0} bones!".format(len(bone_list)))
        # transform, off = import_transform(packed_bytes, off)

    # print(f'Imported {name}!')  
    return header, vertex_list, triangle_list, material_list, bone_list, transform, encrypted


def read_sco(file):
    matls_from_o3d = set()
    meshs_from_sco = set()
    try:
        fole = open(file, 'r', encoding='utf-8').readlines()
    except FileNotFoundError:
        print(f'File {file} not found.')
        with open("did_not_pack.txt", 'a') as f:
            f.write(f'{file}\n')
        return matls_from_o3d, meshs_from_sco
    fole = [each.strip() for each in fole if each.strip() != '']
    count = 0
    file_directory = os.path.dirname(file)
    # print(file_directory)
    # exit()
    # print(file,62+4565)
    # exit()
    while count < len(fole):
        # print(fole[count])
        if fole[count] == '[mesh]':
            o3dfile = fole[count + 1].strip()
            # print(o3dfile)
            # exit()
            try:
                o3d = open(f'{file_directory}/model/{o3dfile}', 'rb')
            except FileNotFoundError:
                print(f'File {o3dfile} not found.')
                count += 1
                continue
            o3d_bytes = o3d.read()
            o3ddd = import_o3d(o3d_bytes, o3dfile)
            matls = o3ddd[3]
            for matl in matls:
                #find strings with texture name
                if matl[4] != None:
                    matls_from_o3d.add(matl[4])
            meshs_from_sco.add(o3dfile)

        if fole[count] == '[matl]':
            matlfile = fole[count + 1].strip()
            matls_from_o3d.add(matlfile)
        count += 1
    return matls_from_o3d, meshs_from_sco



def read_sli(file):
    # print(file)
    try:
        sli = open(file, 'r', encoding='utf-8').readlines()
    except FileNotFoundError:
        print(f'File {file} not found.')
        with open("did_not_pack.txt", 'a') as f:
            f.write(f'{file}\n')
        return set()
    sli = [each.strip() for each in sli if each.strip() != '']
    matls_from_sli = set()
    count = 0
    while count < len(sli):
        if sli[count] == '[texture]':
            matlfile = sli[count + 1].strip()
            # print(matlfile)
            matls_from_sli.add(matlfile)
        count += 1
    return matls_from_sli


def pack_files(source_dir, output_zip_file, file_paths):
    open("did_not_pack.txt", 'w').close()
    file_ls = []
    folder_ls = []
    file_paths = [each.strip() for each in file_paths if each.strip() != '']
    for each1 in file_paths:
        if each1.endswith('.sco'):
            aaa = read_sco(os.path.join(source_dir, each1))
            for each2 in aaa[0]:
                if each2 not in file_paths:
                    file_ls.append(f"{os.path.dirname(each1)}/texture/{each2}")
            for each3 in aaa[1]:
                if each3 not in file_paths:
                    file_ls.append(f"{os.path.dirname(each1)}/model/{each3}")
        if each1.endswith('.sli'):
            # print(each1)
            aaa = read_sli(os.path.join(source_dir, each1))
            print(aaa)
            for each2 in aaa:
                if each2 not in file_paths:
                    file_ls.append(f"{os.path.dirname(each1)}/texture/{each2}")
        if each1.endswith('\\*'):
            each1 = each1[:-1]
            folder_ls.append(each1)

    with zipfile.ZipFile(output_zip_file, 'w') as zip_file:
        for file_path in file_paths:
            if file_path.endswith('\\*'):
                continue
            full_path = os.path.join(source_dir, file_path)
            zip_file.write(full_path, file_path)

        # Include additional files from the lists
        for file_path in file_ls:
            full_path = os.path.join(source_dir, file_path)
            if os.path.exists(full_path):
                zip_file.write(full_path, file_path)
                print(full_path, file_path)
        for folders in folder_ls:
            folder_path = os.path.join(source_dir, folders)
            if os.path.exists(folder_path):
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        file_full_path = os.path.join(root, file)
                        zip_file.write(file_full_path, os.path.relpath(file_full_path, source_dir))
                        print(file_full_path, os.path.relpath(file_full_path, source_dir))
    # print(file_paths)


    # with zipfile.ZipFile(output_zip_file, 'w') as zip_file:
    #     for file_path in file_paths:
    #         print(file_path)
    #         full_path = os.path.join(source_dir, file_path)
    #         zip_file.write(full_path, file_path)
    #         # print(full_path, file_path,file_path.strip().endswith('.sco'))
    #         if file_path.strip().endswith('.sco'):
    #             matls_from_sco = read_sco(full_path)
    #             print(matls_from_sco)
    #             for matl in matls_from_sco[0]:
    #                 matl_path = os.path.join(source_dir, 'texture', matl)
    #                 if os.path.exists(matl_path):
    #                     zip_file.write(matl_path, os.path.relpath(matl_path, source_dir))
    #                     print(matl_path,os.path.relpath(matl_path, source_dir))
    #             for mesh in matls_from_sco[1]:
    #                 mesh_path = os.path.join(source_dir, 'model', mesh)
    #                 if os.path.exists(mesh_path):
    #                     zip_file.write(mesh_path, os.path.relpath(mesh_path, source_dir))
    #                     print(matl_path,os.path.relpath(mesh_path, source_dir))
    #         if file_path.endswith('.sli'):
    #             matls_from_sli = read_sli(full_path)
    #             for matl in matls_from_sli:
    #                 matl_path = os.path.join(source_dir, 'texture', matl)
    #                 if os.path.exists(matl_path):
    #                     zip_file.write(matl_path, os.path.relpath(matl_path, source_dir))
    #                     print(matl_path,os.path.relpath(matl_path, source_dir))
            # # Include 'model' and 'texture' folders and their contents
            # for folder in ['model', 'texture']:
            #     folder_path = os.path.join(os.path.dirname(full_path), folder)
            #     if os.path.exists(folder_path):
            #         for root, _, files in os.walk(folder_path):
            #             for file in files:
            #                 file_full_path = os.path.join(root, file)
            #                 zip_file.write(file_full_path, os.path.relpath(file_full_path, source_dir))
                            
def read_file_paths(file_list_path):
    with open(file_list_path, 'r') as file:
        lines = file.read().splitlines()
        file_paths = lines
        return file_paths

output_zip_file = "packed_files.zip"
file_list_path = "file_paths.txt"
source_directory = '.'
file_paths = read_file_paths(file_list_path)
print(file_paths) 
pack_files(source_directory, output_zip_file, file_paths)
