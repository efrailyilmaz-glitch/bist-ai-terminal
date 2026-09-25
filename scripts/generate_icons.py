from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT=Path("build")
OUT.mkdir(parents=True,exist_ok=True)
size=1024
img=Image.new("RGBA",(size,size),(7,18,26,255))
d=ImageDraw.Draw(img)
d.rounded_rectangle((96,96,928,928),radius=190,fill=(9,30,42,255),outline=(39,187,158,255),width=18)
d.rounded_rectangle((140,140,884,884),radius=160,outline=(49,215,255,180),width=8)
pts=[(250,640),(365,520),(470,585),(590,405),(730,315)]
d.line(pts,fill=(45,214,157,255),width=38,joint="curve")
for x,y in pts:
    d.ellipse((x-22,y-22,x+22,y+22),fill=(66,214,255,255))

font=None
for fp in [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]:
    try:
        font=ImageFont.truetype(fp,160)
        break
    except Exception:
        pass
if font is None:
    font=ImageFont.load_default()

bbox=d.textbbox((0,0),"BA",font=font)
tw=bbox[2]-bbox[0]
d.text(((size-tw)/2,690),"BA",font=font,fill=(238,247,250,255))

img.save(OUT/"icon.png","PNG")
img.save(OUT/"icon.ico","ICO",sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
img.save(OUT/"icon.icns","ICNS")
print("Generated desktop icons in build/")
