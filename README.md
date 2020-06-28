# modpack_dl
A simple tool to download mods and the correct version of Forge for a Curseforge Minecraft modpack. 

There are lots of third-party Minecraft launchers available, but they require you to enter your login credentials into a launcher other than the official one. 
This script aims to avoid that requirement of trust by simply downloading the mods and Forge, leaving you to assemble them in the correct folder and set up a launcher profile. 

The aim is that the code is simple enough to understand that you don't need to worry about what's going on.

## Requirements

* Python 3.8+ (A handy additional argument was added to `copytree()` in this version.)
* A compatible version of the `requests` library (e.g. installed via `apt install python3-requests` or using pip)

## Usage
`python3 modpack_dl.py PATH_TO_MODPACK_ZIP`

A folder will be created in the current working directory with the same name as the zip. For example, after running on `my_pack.zip`, the structure will be:
```
    my_pack/
        minecraft/
        forge_(version).jar
```

To install the pack:
1. Copy or move the contents of `minecraft/` subfolder to where you want the game data to be stored.
1. Create a new profile (or 'installation') in the official launcher
1. Select the correct version of Forge
1. Set the game directory to the folder where you put the contents of `minecraft/`
1. Select the location of your Java 8 installation
1. Set any relevant JVM arguments (most importantly the amount of RAM to allocate, i.e. `-Xmx 3G`)

## Acknowledgements
The unofficial API documentation at https://twitchappapi.docs.apiary.io was absolutely essential.

I got an overview of the process by looking at the source for [MultiMC5](https://github.com/MultiMC/MultiMC5), an open-source third-party launcher.
