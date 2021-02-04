from openslide import open_slide
from openslide.deepzoom import DeepZoomGenerator
import os

def save_dzi(slide_path, output_path, filename):
    try:
        slide = open_slide(slide_path)
        if not os.path.exists(output_path):
            os.mkdir(output_path)
        dzi_file = os.path.join(output_path, filename+'.dzi')
        if os.path.exists(dzi_file):
            return True
        dz = DeepZoomGenerator(slide)
        with open(dzi_file, 'w') as fs:
            fs.write(dz.get_dzi('jpeg'))
        dzi_folder = os.path.join(output_path, filename+'_files')
        
        if not os.path.exists(dzi_folder):
            os.mkdir(dzi_folder)
        
        # Image files
        levels = dz.level_count
        counter = 0
        for i in range(levels):
            level_folder = os.path.join(dzi_folder, str(i))
            level_address = dz.level_tiles[i]
            if not os.path.exists(level_folder):
                os.mkdir(level_folder)
            for r in range(level_address[0]):
                for c in range(level_address[1]):
                    img = dz.get_tile(i, (r, c))
                    img_name = os.path.join(level_folder, str(r)+'_'+str(c)+'.jpeg')
                    img.save(img_name, "JPEG", quality=90, optimize=True)
                    counter += 1
        return True
    except Exception:
        return None
