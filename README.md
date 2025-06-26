# Yet Another Addon
This is a Blender add-on which aims to give various tools to aid in XIV Modding workflows. Some of its features are:
* Fix for transparent meshes made in Blender.
* XIV .pose and scaling import.
* File export with ability to retain XIV specific properties.
* Penumbra compatible modpackaging.

A more extensive overview of the features can be found [here](https://docs.google.com/document/d/1WRKKUZZsAzDOTpt6F7iJkN8TDvwDBm0s0Z4DHdWqT_o/edit?usp=sharing), as well as the compatible YAB+ Devkit.

You'll find most of the features under the "XIV Kit" tab in the 3D Viewport.

## Installing
For automatic updates, you should install this as a Blender Extension by adding this URL to Blender's extension repositories:
- https://raw.githubusercontent.com/Arrenval/Yet-Another-Addon/refs/heads/main/repo.json

Installing this as an addon and later updating to an extension will incur a loss of user preferences, and vice versa.

## Licensing
Modules based around Penumbra and XIV interop are standalone, exist for compatibility and do not interface directly with the Blender Python API. They inherit their respective source's licenses. See **Acknowledgements** for details.

The remaining code within this tool is made for the Blender API and follows its GPL3 licensing, read the *LICENSE.md* for details. However, I do humbly request that it does not be used for creating mods 
or assets that are behind a permanent paywall. 

## Acknowledgements
* The `penumbra` module is based around Penumbra's [Modpack schemas](https://github.com/xivdev/Penumbra/tree/master/schemas) by Ottermandias and Ny.
