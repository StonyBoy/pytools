#! /usr/bin/env python3
'''
Use JPEG photo as wallpaper images.

You can rename image files and convert, size and crop them
You can also set them as lockscreen or wallpaper
'''
import os
import os.path
import argparse
from PIL import Image
import random
import subprocess

def set_sway_wallpaper():
    print('set sway wallpaper')
    subprocess.run(['swaymsg', 'output * bg /opt/wallpapers/wallpaper.jpg fill'])

def set_i3_wallpaper():
    print('set i3 wallpaper')
    subprocess.run(['feh', '--bg-fill', '/opt/wallpapers/wallpaper.jpg'])

def rename_file(filename):
    if (filename.endswith('.jpg') or filename.endswith('.JPG')) and not filename.startswith('.'):
        newname = filename.replace(' ', '-').lower()
        if newname != filename:
            print('{} -> {}'.format(filename, newname))
            os.rename(filename, newname)


def show_fileinfo(fullpath):
    with Image.open(fullpath) as image:
        print(fullpath, image.format, "%dx%d" % image.size, image.mode)


def scale_to_display(newfullpath, fullpath, displaysize, crop_percentage):
    with Image.open(fullpath) as image:
        if image.size[0] / image.size[1] > displaysize[0] / displaysize[1]:
            print('Crop from left using {}%'.format(crop_percentage))
            # Larger aspect ratio, use fixed height: displayheight
            newsize = int(image.size[0] / image.size[1] * displaysize[1]), displaysize[1]
            newimage = image.resize(newsize)
            # Crop from Left Box: left, upper, right, and lower pixel coordinate.
            startx = (newsize[0]-displaysize[0]) * crop_percentage // 100
            box = startx, 0, startx + displaysize[0], displaysize[1]
            print('imagesize {} on display {} resized to {} and crop box {}'.format(image.size, displaysize, newsize, box))
            croppedimage = newimage.crop(box)
            croppedimage.save(newfullpath)
        else:
            print('Crop from top using {}%'.format(crop_percentage))
            newsize = displaysize[0], int(displaysize[0] / image.size[0] * image.size[1])
            newimage = image.resize(newsize)
            # Crop from Top Box: left, upper, right, and lower pixel coordinate.
            starty = (newsize[1]-displaysize[1]) * crop_percentage // 100
            box = 0, starty, displaysize[0], starty + displaysize[1]
            print('imagesize {} on display {} resized to {} and crop box {}'.format(image.size, displaysize, newsize, box))
            croppedimage = newimage.crop(box)
            croppedimage.save(newfullpath)


def select_random_image(filepath):
    images = [p for p in os.listdir(filepath) if p.endswith('.jpg')]
    choice = random.randrange(len(images))
    return os.path.join(filepath, images[choice])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-i', dest='info', help='Show image information', action='store_true')
    parser.add_argument('-x', dest='display_width', help='Display Width', type=int, default=1920)
    parser.add_argument('-y', dest='display_height', help='Display Height', type=int, default=1200)
    parser.add_argument('-c', dest='crop_percentage', help='Crop from left or top percentage (0-100)', type=int, default=50)
    parser.add_argument('-n', dest='rename', help='Rename files with lowercase and no spaces', action='store_true')
    parser.add_argument('-l', dest='lockfile', help='Create lockscreen.jpg file', action='store_true')
    parser.add_argument('-w', dest='wallpaper', help='Create wallpaper.jpg file', action='store_true')
    parser.add_argument('-a', dest='sway', help='Update sway background with wallpaper.jpg file', action='store_true')
    parser.add_argument('-t', dest='i3', help='Update i3 background with wallpaper.jpg file', action='store_true')
    parser.add_argument('-s', dest='login', help='Create login_screen.jpg file', action='store_true')
    parser.add_argument('-r', dest='random', help='Select a random image from the specified path', action='store_true')
    parser.add_argument('filenames', help='Image file or a path to images', nargs='*', metavar='path')
    args = parser.parse_args()
    if len(args.filenames):
        for filename in args.filenames:
            fullpath = os.path.abspath(filename)
            if args.info:
                show_fileinfo(fullpath)
            elif args.rename:
                rename_file(fullpath)
            if args.random:
                fullpath = select_random_image(fullpath)
                print('Selected', fullpath)
            if args.lockfile:
                newname = 'lockscreen.jpg'
            elif args.wallpaper:
                newname = 'wallpaper.jpg'
            elif args.login:
                newname = 'login_wallpaper.jpg'
            else:
                newname = 'cropped_image.jpg'
            newfullpath = os.path.join(os.path.dirname(fullpath), newname)
            scale_to_display(newfullpath, fullpath, (args.display_width, args.display_height), args.crop_percentage)
            print('Created', newfullpath)
            if args.sway:
                set_sway_wallpaper()
            elif args.i3:
                set_i3_wallpaper()
