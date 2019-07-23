# Blender Export X for Richard Burns Rally editor
RBR editor needs imported mesh to meet many requirements, otherwise the model can't be imported without errors.
This Blender 2.79 addon prepares and exports the mesh so it can be imported straight away, without any manual fixes.

## What does it do:
- cleans the mesh (reveal hidden vertices, remove doubles, delete loose)
- applies transformations
- separates by material
- splits the mesh into chunks using the user settings (by max. vertex count and max. length)
- rotates & mirrors the model as necessary (in case of exporting General / Ground Mesh)
- exports to X (using the appropriate DirectX exporter settings)
- divides the export to multiple .x files based on the max. vertex count per file settings (to avoid crashes on import)
![](readme-files/screen1.png)

## Tip:
- apply this 4GB patcher to editor .exe file, this allows you to import 2x large files https://ntcore.com/?page_id=371
- after applying the patch, you should be fine just with the default settings, which are:
  - max. vertex count per chunk: 25 000
  - max. length of chunk: 200 (meters)
  - max. vertex count per .x file: 800 000 (even 1M should be OK, you just need to stay below 300MB to avoid crashes on import, ideally around 260MB)
  
  [[![](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=35AZKW44A96QQ&item_name=Particles+Density+-+Blender+Addon&currency_code=CZK&source=url)
 
