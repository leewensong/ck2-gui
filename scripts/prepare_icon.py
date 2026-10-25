"""Convert the user-maintained PNG into a multi-resolution Windows icon."""
from pathlib import Path
import argparse
from PIL import Image

parser=argparse.ArgumentParser()
parser.add_argument('source',nargs='?',type=Path,default=Path(__file__).resolve().parents[1]/'packaging/app.png')
parser.add_argument('--output',type=Path)
args=parser.parse_args()
output=args.output or args.source.with_suffix('.ico')
image=Image.open(args.source).convert('RGBA')
if image.size != (256,256):
    image.thumbnail((256,256),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(256,256))
    canvas.alpha_composite(image,((256-image.width)//2,(256-image.height)//2))
    image=canvas
image.save(output,format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(output.resolve())
