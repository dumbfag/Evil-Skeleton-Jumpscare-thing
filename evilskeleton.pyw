import ctypes
import random
import time
from infi.systray import SysTrayIcon
import tkinter as tk
from tkinter import ttk, messagebox
from screeninfo import get_monitors
import json
import pygame
import win32api
import win32con
import win32gui
import winreg
import sys
import os
import cv2
import numpy as np
import av

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

tray_icon_path = os.path.join(base_path, "skellicon.ico")
settings_path = os.path.join(base_path, "settings.json")
video_path = os.path.join(base_path, "evil_skeleton.webm")

def on_quit(icon):
    os._exit(0)

def resource_path(filename):
    return os.path.join(base_path, filename)

paused = False
test = False

def do_the_thing(systray):
    global test
    test = True

def pause(systray):
    global paused
    paused = True

def resume(systray):
    global paused
    paused = False

def settings(systray):
    root = tk.Tk()
    root.title("Settings")
    root.geometry("400x320")

    tk.Label(root, text="Adjust settings below:").pack(pady=10)

    def validate_input(P):
        return P == "" or P.isdigit()

    vcmd = (root.register(validate_input), '%P')

    # grid thingymabob

    frame = tk.Frame(root)
    frame.pack(padx=10, pady=5)

    header = tk.Label(frame, text="wait time (seconds)", font=("Arial", 12, "bold"))
    header.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))

    tk.Label(frame, text="minimum wait:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
    min_entry = tk.Entry(frame, width=10, validate="key", validatecommand=vcmd)
    min_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

    tk.Label(frame, text="maximum wait:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
    max_entry = tk.Entry(frame, width=10, validate="key", validatecommand=vcmd)
    max_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

    # checkbox

    checkbox_var = tk.BooleanVar()
    tk.Checkbutton(root, text="Enable on startup", variable=checkbox_var).pack(anchor="w", padx=10, pady=5)

    # load settings

    try:
        with open("settings.json", "r") as f:
            loaded = json.load(f)
        if "enable_on_startup" in loaded:
            checkbox_var.set(loaded["enable_on_startup"])
        if "min_wait" in loaded:
            min_entry.insert(0, loaded["min_wait"])
        if "max_wait" in loaded:
            max_entry.insert(0, loaded["max_wait"])
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # startup registry stuff

    APP_NAME = "EvilSkeleton"
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

    def get_startup_command():
        if getattr(sys, 'frozen', False):
            return f'"{sys.executable}"'
        else:
            script = os.path.abspath(sys.argv[0])
            pythonw = sys.executable.replace("python.exe", "pythonw.exe")
            return f'"{pythonw}" "{script}"'

    def set_startup(enabled):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_startup_command())
                else:
                    winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass

    # save settings

    def save():
        data = {
            "enable_on_startup": checkbox_var.get(),
            "min_wait": min_entry.get(),
            "max_wait": max_entry.get()
        }
        with open("settings.json", "w") as f:
            json.dump(data, f)

        set_startup(checkbox_var.get())
        messagebox.showinfo("Saved", "Settings saved!")

    tk.Button(root, text="Save Changes", command=save).pack(pady=5)
    tk.Button(root, text="Close", command=root.destroy).pack(pady=5)

    root.mainloop()


menu_options = (("Do the thing", None, do_the_thing), ("Pause", None, pause), ("Resume", None, resume), ("Settings", None, settings))
systray = SysTrayIcon("skellicon.ico", "Evil skeleton", menu_options, on_quit=on_quit)
systray.start()


# load timer settings


timerminwait = 0
timermaxwait = 0

try:
    with open("settings.json", "r") as f:
        loaded = json.load(f)
    if "min_wait" in loaded:
        timerminwait = float(loaded["min_wait"])
    if "max_wait" in loaded:
        timermaxwait = float(loaded["max_wait"])
except (FileNotFoundError, json.JSONDecodeError):
    pass


# de loop 


def randomloop(timerminwait, timermaxwait):
    print("working...")
    interval = random.uniform(timerminwait, timermaxwait)

    video_path = resource_path("evil_skeleton.webm")

    # open video
    container = av.open(video_path)
    stream = container.streams.video[0]
    ctypes.windll.user32.SetProcessDPIAware()
    pygame.init()
    info = pygame.display.Info()
    width  = ctypes.windll.user32.GetSystemMetrics(0)
    height = ctypes.windll.user32.GetSystemMetrics(1)
    fps = int(stream.average_rate) if stream.average_rate else 30

    # pygame stuff
    screen = pygame.display.set_mode((width, height), pygame.NOFRAME)
    transparency_color = (0,0,0)  #colour key for transparency

    # win32 stuff
    hwnd = pygame.display.get_wm_info()["window"]
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
        win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*transparency_color), 0, win32con.LWA_COLORKEY)
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

    # playback loop
    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        try:
            frame = next(container.decode(video=0))
        except StopIteration:
            break  

        img = frame.to_ndarray(format="rgba")  

        # resize
        if img.shape[1] != width or img.shape[0] != height:
            img = cv2.resize(img, (width, height), interpolation=cv2.INTER_LINEAR)

        alpha = img[:, :, 3]
        img[alpha == 0] = [255, 0, 255, 255]

        surface = pygame.image.frombuffer(img.tobytes(), (width, height), "RGBA")

        screen.fill(transparency_color)
        screen.blit(surface, (0, 0))
        pygame.display.flip()
        clock.tick(fps)

    container.close()
    pygame.quit()
    test = False

next_run = time.time() + random.uniform(timerminwait, timermaxwait)

while True:
    if test:
        test = False
        next_run = time.time() + random.uniform(timerminwait, timermaxwait)
        randomloop(timerminwait, timermaxwait)
    elif not paused and time.time() >= next_run:
        randomloop(timerminwait, timermaxwait)
        next_run = time.time() + random.uniform(timerminwait, timermaxwait)
    else:
        time.sleep(0.05)