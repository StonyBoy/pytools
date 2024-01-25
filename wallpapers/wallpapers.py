#! /usr/bin/env python3
'''
Use JPEG photo as wallpaper images.

You can rename image files and convert, size and crop them
You can also set them as lockscreen or wallpaper

Dependencies:

    pip install Pillow
'''
import os
import os.path
import argparse
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import random
import subprocess
import socket
import datetime


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--info', '-i', help='Show image information', action='store_true')
    parser.add_argument('--display_width', '-x', help='Display Width', type=int, default=2560)
    parser.add_argument('--display_height', '-y', help='Display Height', type=int, default=1440)
    parser.add_argument('--crop', '-c', help='Crop from left or top percentage (0-100)', type=int, default=50)
    parser.add_argument('--rename', '-n', help='Rename files with lowercase and no spaces', action='store_true')
    parser.add_argument('--lockfile', '-l', help='Create lockscreen.jpg file', action='store_true')
    parser.add_argument('--wallpaper', '-w', help='Create wallpaper.jpg file', action='store_true')
    parser.add_argument('--sway', '-a', help='Update sway background with wallpaper.jpg file', action='store_true')
    parser.add_argument('--i3', '-t', help='Update i3 background with wallpaper.jpg file', action='store_true')
    parser.add_argument('--login', '-s', help='Create login_screen.jpg file', action='store_true')
    parser.add_argument('--random', '-r', help='Select a random image from the specified path', action='store_true')
    parser.add_argument('--system_info', '-z', help='Add text about the system to the final image', action='store_true')
    parser.add_argument('filenames', help='Image file or a path to images', nargs='*', metavar='path')
    return parser.parse_args(), parser


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


def scale_to_display(newfullpath, fullpath, displaysize, crop):
    with Image.open(fullpath) as image:
        if image.size[0] / image.size[1] > displaysize[0] / displaysize[1]:
            print('Crop from left using {}%'.format(crop))
            # Larger aspect ratio, use fixed height: displayheight
            newsize = int(image.size[0] / image.size[1] * displaysize[1]), displaysize[1]
            newimage = image.resize(newsize)
            # Crop from Left Box: left, upper, right, and lower pixel coordinate.
            startx = (newsize[0] - displaysize[0]) * crop // 100
            box = startx, 0, startx + displaysize[0], displaysize[1]
            print('imagesize {} on display {} resized to {} and crop box {}'
                  .format(image.size, displaysize, newsize, box))
            croppedimage = newimage.crop(box)
            croppedimage.save(newfullpath)
        else:
            print('Crop from top using {}%'.format(crop))
            newsize = displaysize[0], int(displaysize[0] / image.size[0] * image.size[1])
            newimage = image.resize(newsize)
            # Crop from Top Box: left, upper, right, and lower pixel coordinate.
            starty = (newsize[1] - displaysize[1]) * crop // 100
            box = 0, starty, displaysize[0], starty + displaysize[1]
            print('imagesize {} on display {} resized to {} and crop box {}'
                  .format(image.size, displaysize, newsize, box))
            croppedimage = newimage.crop(box)
            croppedimage.save(newfullpath)


def select_random_image(filepath):
    images = [p for p in os.listdir(filepath) if p.endswith('.jpg')]
    choice = random.randrange(len(images))
    return os.path.join(filepath, images[choice])


def draw_text(draw, text, size=100, top=10, left=10, outline=2):
    shadowcolor = (250, 250, 250)
    try:
        font = ImageFont.truetype('Inconsolata-Regular.ttf', size)
    except OSError:
        font = ImageFont.truetype('Inconsolata.otf', size)
    # Add an outline
    draw.text((top - outline, left - outline), text, font=font, fill=shadowcolor)
    draw.text((top + outline, left - outline), text, font=font, fill=shadowcolor)
    draw.text((top - outline, left + outline), text, font=font, fill=shadowcolor)
    draw.text((top + outline, left + outline), text, font=font, fill=shadowcolor)
    # Text on top
    draw.text((top, left), text, font=font, fill=(255, 0, 0))
    return top + size


def add_system_info(args, filepath, top=10, left=10):
    hostname = os.uname().nodename
    ipv4addr = socket.gethostbyname(hostname)

    now = datetime.date.today().strftime('%d-%b-%Y')
    img = Image.open(filepath)
    draw = ImageDraw.Draw(img)
    size = 60
    top += draw_text(draw, f'User: {os.environ["USER"]}', size, left, top)
    top += draw_text(draw, f'Hostname: {hostname}', size, left, top)
    top += draw_text(draw, f'IPv4: {ipv4addr}', size, left, top)
    top += draw_text(draw, f'Date: {now}', size, left, top)
    img.save(filepath)


if __name__ == '__main__':
    args, parser = parse_arguments()

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
            scale_to_display(newfullpath, fullpath, (args.display_width, args.display_height), args.crop)
            add_system_info(args, newfullpath)
            print('Created', newfullpath)
            if args.sway:
                set_sway_wallpaper()
            elif args.i3:
                set_i3_wallpaper()
    else:
        parser.print_help()
