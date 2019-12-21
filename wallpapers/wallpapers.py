#! /usr/bin/env python3
'''
Use JPEG photo as wallpaper images.

You can rename image files and convert, size and crop them
You can also set them as I3 lockfile or I3 wallpaper
'''
import os
import os.path
import argparse
import sys
from PIL import Image
import random


def rename_file(filename):
    if (filename.endswith('.jpg') or filename.endswith('.JPG')) and not filename.startswith('.'):
        newname = filename.replace(' ', '-').lower()
        if newname != filename:
            print('{} -> {}'.format(filename, newname))
            os.rename(filename, newname)


def show_fileinfo(fullpath):
    with Image.open(fullpath) as image:
        print(fullpath, image.format, "%dx%d" % image.size, image.mode)


def scale_to_display_as_png(fullpath, displaysize, crop_percentage):
    if fullpath.endswith('.jpg'):
        newfullpath = fullpath.replace('.jpg', '.png')
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
                return newfullpath
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
                return newfullpath
    return None


def link_to_file(fullpath, name):
    print(fullpath, name)
    image_folder = os.path.dirname(fullpath)
    linkpath = os.path.join(image_folder, name)
    if os.path.exists(linkpath):
        os.remove(linkpath)
    os.symlink(fullpath, linkpath)


def select_random_image(filepath):
    images = [p for p in os.listdir(filepath) if p.endswith('.jpg')]
    choice = random.randrange(len(images))
    return os.path.join(filepath, images[choice])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-i', dest='info', help='Show image information', action='store_true')
    parser.add_argument('-p', dest='png', help='Convert to a display scaled and cropped PNG file', action='store_true')
    parser.add_argument('-x', dest='display_width', help='Display Width', type=int, default=1920)
    parser.add_argument('-y', dest='display_height', help='Display Height', type=int, default=1200)
    parser.add_argument('-c', dest='crop_percentage', help='Crop from left or top percentage (0-100)', type=int, default=50)
    parser.add_argument('-n', dest='rename', help='Rename files with lowercase and no spaces', action='store_true')
    parser.add_argument('-l', dest='lockfile', help='Link image to I3 lockfile', action='store_true')
    parser.add_argument('-w', dest='wallpaper', help='Link image to I3 wallpaper', action='store_true')
    parser.add_argument('-s', dest='login', help='Link image to lightdm login screen wallpaper', action='store_true')
    parser.add_argument('-r', dest='random', help='Select a random image from the specified path', action='store_true')
    parser.add_argument('filenames', help='Image file or a path to images', nargs='*', metavar='path')
    args = parser.parse_args()
    if len(args.filenames):
        for filename in args.filenames:
            fullpath = os.path.abspath(filename)
            if args.info:
                show_fileinfo(fullpath)
            elif args.png:
                if args.random:
                    fullpath = select_random_image(fullpath)
                    print('Selected', fullpath)
                newfullpath = scale_to_display_as_png(fullpath, (args.display_width, args.display_height), args.crop_percentage)
                if args.lockfile:
                    link_to_file(newfullpath, 'i3lock.png')
                elif args.wallpaper:
                    link_to_file(newfullpath, 'i3wallpaper.jpg')
                elif args.login:
                    link_to_file(newfullpath, 'login_wallpaper.png')
            elif args.rename:
                rename_file(fullpath)
