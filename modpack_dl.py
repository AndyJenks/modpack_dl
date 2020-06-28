#!/usr/bin/env python3
# modpack_dl.py - Andrew Jenkins 2020
# Version 0.0.1
# Downloads the files for a twitch/curse Minecraft modpack starting from its
# zip archive.
# Based on looking at MultiMC 5 https://github.com/MultiMC/MultiMC5
# and also at this api https://twitchappapi.docs.apiary.io/

import sys
import zipfile
import json
import os
import shutil
import urllib
import subprocess
import tempfile

import requests

api_url = "https://addons-ecs.forgesvc.net/api/v2/"
headers = {'user-agent': 'modpack_dl.py/0.0.1'}

s = requests.Session()
s.headers.update(headers)

def get_manifest(mod_zip):
    # mod_zip should be a zipfile object
    with mod_zip.open("manifest.json") as jf:
        return json.load(jf)

def is_modpack_zip(fpath):
    if not zipfile.is_zipfile(fpath):
        return False
    else:
        try:
            with zipfile.ZipFile(fpath, "r") as zf:
                mf = get_manifest(zf)
                return mf["manifestType"] == "minecraftModpack"
        except KeyError: # this is if the manifest does not exist.
            return False

def get_download_url(proj_id, file_id):
    
    # don't want injection of stuff here.
    assert isinstance(proj_id, int)
    assert isinstance(file_id, int)
    
    req_url = "{}addon/{}/file/{}/download-url".format(api_url, proj_id, file_id)
    #print(req_url)
    response = s.get(req_url)
    response.raise_for_status()
    return response.text

def get_info(proj_id):
    assert isinstance(proj_id, int)
    
    req_url = "{}addon/{}".format(api_url, proj_id)
    
    response = s.get(req_url)
    response.raise_for_status()
    
    return response.json()
    
def output_dir_for_zip(fname):
    filename = os.path.basename(fname)
    if filename.endswith(".zip"):
        return filename[:-4]
    else:
        return filename

def is_subdir(a, b):
    # Is A a subdir of B?
    abs_a = os.path.abspath(a)
    abs_b = os.path.abspath(b)
    
    return os.path.commonpath([abs_a, abs_b]) == abs_b

def download_to_file(url, file, overwrite=False):
    
    if os.path.exists(file) and not overwrite:
        raise FileExistsError(file)
    
    # so partially-downloaded files don't cause us any problems
    dlpath = file + ".part" 
    
    r = s.get(url, stream=True)
    r.raise_for_status()
    
    with open(dlpath, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=1024):
            fd.write(chunk)

    shutil.move(dlpath, file)


def download_manifest_file(f, folder, force=False):
    # `file' is a file record from the manifest, viz: 
    #   {proj_id: int, file_id: int, required: bool}
    
    # if force is true then the file will be downloaded even if there is already
    # a file with that name in the folder.
    
    mod_info = get_info(f["projectID"])
    url = get_download_url(f["projectID"], f["fileID"])
    
    # i.e. https://www.example.com/my/filename.jar -> filename.jar
    
    filename = url.split("/")[-1]
    destpath = os.path.join(folder, filename)
    
    # this is what MultiMC does for non-required mods.
    if not f["required"]:
        destpath = destpath + ".disabled"
    
    if os.path.exists(destpath) and not force:
        # if it already exists and we're not forcing it then skip
        print("    Reused {}".format(mod_info["name"]))
    else:
        print("    Downloading {}".format(mod_info["name"]))
        download_to_file(url, destpath)
            
def get_modloader_info(modloader_id):
    
    req_url = "{}minecraft/modloader/{}".format(api_url, urllib.parse.quote(modloader_id))
    response = s.get(req_url)
    response.raise_for_status()
    
    return response.json()
    
def extract_overrides(mpack_zip, output_dir):

    with tempfile.TemporaryDirectory() as tempd:    
    
        or_folder = get_manifest(mpack_zip)['overrides']
        for n in mpack_zip.namelist():
            if n.startswith(or_folder):
                mpack_zip.extract(n, tempd)
    
        output_override_dir = os.path.join(tempd, or_folder)

        # don't want to touch anything outside of this dir    
        assert is_subdir(output_override_dir, tempd)
        
        shutil.copytree(output_override_dir, output_dir, dirs_exist_ok=True)

def main(argv):
    tgt_zip = argv[1]
    
    if "-h" in argv or "--help" in argv:
        print("USAGE: modpack_dl.py MODPACK_ZIP\n"\
              "    See the README for instructions to make it playable")
    
    if not is_modpack_zip(tgt_zip):
        print("'{}' is not a valid modpack zip.".format(tgt_zip))
    else:
        out_dname = output_dir_for_zip(tgt_zip)
        
        if os.path.isdir(out_dname):
            print("Output directory {} already exists, contents may be overwritten.".format(out_dname))
        else:
            os.mkdir(out_dname)
            
        with zipfile.ZipFile(tgt_zip) as zf:
            mf = get_manifest(zf)
            
            print ("Modpack: {name} {version} by {author}".format(**mf))
            
            if 'overrides' in mf:
                print("Extracting overrides.")
                extract_overrides(zf, os.path.join(out_dname, "minecraft"))
        
        print("Creating mod folder.")
        mod_output_dir = os.path.join(out_dname, "minecraft", "mods")
        os.makedirs(mod_output_dir, exist_ok=True)
        
        print("Downloading {} mods...".format(len(mf["files"])))
        for f in mf["files"]:
            download_manifest_file(f, mod_output_dir)
        
        print("Retrieving Forge...")
        loaders = mf["minecraft"]["modLoaders"]
        for l in loaders:
            if l["primary"]:
                modloader_id = l["id"]
        
        loader_info = get_modloader_info(modloader_id)
        if "downloadUrl" in loader_info:
            dest_fname = loader_info["filename"]
            dest_path = os.path.join(out_dname, dest_fname)
            url = loader_info["downloadUrl"]
            
            # we want the 'installer' forge jar because this is only minimally 
            # automated.
            if not dest_path.endswith("-installer.jar"):
                dest_path = dest_path[:-4] + "-installer.jar"
                url = url[:-4] + "-installer.jar"
            try:
                print("    Downloading '{}'".format(loader_info["name"]))
                download_to_file(url, dest_path)
            except FileExistsError:
                pass
            
            print("Running Forge installer.")
            rslt = subprocess.run(["java", "-jar", dest_path], 
                                  stdout=subprocess.DEVNULL, 
                                  stderr=subprocess.DEVNULL)
            print("Done.")
        else:
            print("Could not get download link for modloader '{}'".format(modloader_id))
    
if __name__ == "__main__":
    main(sys.argv)
