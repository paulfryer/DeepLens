from PIL import Image
from PIL import ImageChops
from PIL import ImageDraw
 
 

file1 = 'TestImages/i1.jpg'
file2 = 'TestImages/i2.jpg'

im1 = Image.open(file1)
im2 = Image.open(file2)

diff = ImageChops.difference(im1, im2).getbbox()

print(diff)




i1 = Image.open("TestImages/Lenna100.jpg")
i2 = Image.open("TestImages/Lenna50.jpg")
assert i1.mode == i2.mode, "Different kinds of images."
assert i1.size == i2.size, "Different sizes."
 
pairs = zip(i1.getdata(), i2.getdata())
if len(i1.getbands()) == 1:
    # for gray-scale jpegs
    dif = sum(abs(p1-p2) for p1,p2 in pairs)
else:
    dif = sum(abs(c1-c2) for p1,p2 in pairs for c1,c2 in zip(p1,p2))
 
ncomponents = i1.size[0] * i1.size[1] * 3
percentDiff = (dif / 255.0 * 100) / ncomponents
print "Difference (percentage):", percentDiff