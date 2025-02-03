import struct
import enum
import numpy as np
import math
import sys
import csv
from dataclasses import dataclass, field

inpath = sys.argv[1]
outpath = sys.argv[2]

@dataclass
class Vector2f:
    x: float
    y: float

    @staticmethod
    def zero():
        return Vector2f(0, 0)

'''
@dataclass
class Vector3f:
    x: float
    y: float
    z: float

    @staticmethod
    def zero():
        return Vector3f(0, 0, 0)


@dataclass
class Matrix33f:
    xx: float
    xy: float
    xz: float
    yx: float
    yy: float
    yz: float
    zx: float
    zy: float
    zz: float

    @staticmethod
    def ident():
        return Matrix33f(1, 0, 0,
                         0, 1, 0,
                         0, 0, 1)


@dataclass
class Gyro:
    direction: Matrix33f
    ang_vel: Vector3f

    @staticmethod
    def zero():
        return Gyro(Matrix33f.ident(), Vector3f.zero())
'''

@dataclass
class Frame:
    duration: int
    buttons: list[str]
    left_stick: Vector2f
    right_stick: Vector2f
    #accel_left: Vector3f
    #accel_right: Vector3f
    #gyro_left: Gyro
    #gyro_right: Gyro

    def to_array(self):
        arr = []
        arr.append(self.duration)
        for button in self.buttons:
            arr.append(button)
        for i in range(max_buttons - len(self.buttons)):
            arr.append("")
        if (self.left_stick == Vector2f.zero()):
            arr.append("")
        else:
            arr.append("lsx(" + str(self.left_stick.x) + "; " + str(self.left_stick.y) + ")")
        if (self.right_stick == Vector2f.zero()):
            arr.append("")
        else:
            arr.append("rsx(" + str(self.right_stick.x) + "; " + str(self.right_stick.y) + ")")

        return arr

max_buttons = 0 #max buttons in a frame

frame_idx_old = -1

frames = []

with open(inpath) as infile:
    for line in infile:
        frame_idx, buttons, left_stick, right_stick = line.split()
        frame_idx = int(frame_idx)
        buttons = buttons.split(";")
        left_stick = left_stick.split(";")
        right_stick = right_stick.split(";")
        #accel_left = accel_left.split(";")
        #accel_right = accel_right.split(";")
        #gyro_dir_left = gyro_dir_left.split(";")
        #angvel_left = angvel_left.split(";")
        #gyro_dir_right = gyro_dir_right.split(";")
        #angvel_right = angvel_right.split(";")

        button_list = []
        for button in buttons:
            if button == "KEY_A": button_list.append("a")
            elif button == "KEY_B": button_list.append("b")
            elif button == "KEY_X": button_list.append("x")
            elif button == "KEY_Y": button_list.append("y")
            elif button == "KEY_L": button_list.append("m-d")
            elif button == "KEY_R": button_list.append("r")
            elif button == "KEY_ZL": button_list.append("zl")
            elif button == "KEY_ZR": button_list.append("zr")
            elif button == "KEY_PLUS": button_list.append("+")
            elif button == "KEY_MINUS": button_list.append("-")
            elif button == "KEY_DUP": button_list.append("m-uu")
            elif button == "KEY_DRIGHT": button_list.append("m-rr")
            elif button == "KEY_DDOWN": button_list.append("m-dd")
            elif button == "KEY_DLEFT": button_list.append("m-ll")
            elif button == "KEY_LSTICK": button_list.append("ls")
            elif button == "KEY_RSTICK": button_list.append("rs")

        if len(button_list) > max_buttons:
            max_buttons = len(button_list)

        ls_x, ls_y = int(left_stick[0]), int(left_stick[1])
        rs_x, rs_y = int(right_stick[0]), int(right_stick[1])

        if ls_x == 0 and ls_y == 0:
            left_stick = Vector2f.zero()
        else:
            left_stick = Vector2f(ls_x, ls_y)

        if rs_x == 0 and rs_y == 0:
            right_stick = Vector2f.zero()
        else:
            right_stick = Vector2f(rs_x, rs_y)

        #accel_left = Vector3f(*map(float, accel_left))
        #accel_right = Vector3f(*map(float, accel_right))

        #gyro_dir_left = Matrix33f(*map(float, gyro_dir_left))
        #angvel_left = Vector3f(*map(float, angvel_left))

        #gyro_dir_right = Matrix33f(*map(float, gyro_dir_right))
        #angvel_right = Vector3f(*map(float, angvel_right))

        #gyro_left = Gyro(gyro_dir_left, angvel_left)
        #gyro_right = Gyro(gyro_dir_right, angvel_right)

        numSkipped = frame_idx - frame_idx_old - 1

        if numSkipped > 0:           
            frame = Frame(numSkipped, [], Vector2f.zero(), Vector2f.zero())
            frames.append(frame)

        #check for repeated frames
        if len(frames) > 0 and frames[-1].buttons == button_list and frames[-1].left_stick == left_stick and frames[-1].right_stick == right_stick:
            # Separate D-pad buttons into a new frame if they exist
            dpad_buttons = [button for button in button_list if button in ["m-ll", "m-uu", "m-rr", "m-dd", "m-d", "m-u", "m-r", "m-l","m"]]
            if dpad_buttons:
                dpad_frame = Frame(1, dpad_buttons, Vector2f.zero(), Vector2f.zero())
                frames.append(dpad_frame)
                button_list = [button for button in button_list if button not in dpad_buttons]
            frames[-1].duration += 1
        else:
            frame = Frame(1, button_list, left_stick, right_stick)
            frames.append(frame)

        frame_idx_old = frame_idx
    
for i in range(len(frames)+1):
    dpad_buttons = [button for button in frames[i -1].buttons if button in ["m-ll", "m-uu", "m-rr", "m-dd", "m-d", "m-u", "m-r", "m-l","m"]]
    # print(dpad_buttons, i)
    if dpad_buttons and frames[i - 1].duration == 1:
        frames[i].buttons = [button for button in frames[i].buttons if button not in dpad_buttons]
        frames[i - 1].buttons.extend(dpad_buttons)
    elif dpad_buttons:
        frames[i].buttons = [button for button in frames[i].buttons if button not in dpad_buttons]
        frames[i - 1].duration -= 1
        new_frame = Frame(1, dpad_buttons + frames[i-1].buttons, frames[i-1].left_stick, frames[i-1].right_stick)
        frames.insert(i, new_frame)
 
        
infile.close()

outfile = open(outpath, "w")

tsv_writer = csv.writer(outfile, delimiter = '\t', lineterminator='\n',)

for frame in frames:
    tsv_writer.writerow(frame.to_array())
