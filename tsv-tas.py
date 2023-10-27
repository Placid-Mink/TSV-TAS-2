import math
import struct
import enum
import sys
from ftplib import FTP
import json
import re
import csv
from dataclasses import dataclass, field

#default gyroscope rotation is 3x3 identity matrix

ANG_VEL_FACTOR = -3/200.0

ftp = False
debug = False

if (sys.argv[1][0] == '-'):
    options = sys.argv[1]
    infile = sys.argv[2]
    outfile = sys.argv[3]
    ftp = "f" in options
    debug = "d" in options

else:
    infile = sys.argv[1]
    outfile = sys.argv[2]
    
if infile.endswith(".tsv"):
    separator = "\t"
elif infile.endswith(".csv"):
    separator = ","
else:
    print("Invalid file type")
    quit(-1)
stage_name = ""
entrance = ""
scenario = 1
independent_gyro = False #if True, can set angular velocity independently of rotation, if False angular velocity calculated from rotation
remove_empty = False #won't work until mod treats y accel as -1

@dataclass
class Vector2f:
    x: float
    y: float

    @staticmethod
    def zero():
        return Vector2f(0, 0)


@dataclass
class Vector3f:
    x: float
    y: float
    z: float
    @staticmethod
    def zero():
        return Vector3f(0, 0, 0)

    @staticmethod
    def default_accel():
        #return Vector3f(0, -1, 0)
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
    euler: Vector3f
    direction: Matrix33f
    ang_vel: Vector3f

    @staticmethod
    def zero():
        return Gyro(Vector3f.zero(), Matrix33f.ident(), Vector3f.zero())


@dataclass
class Frame:
    step: int
    second_player: bool
    buttons: int
    left_stick: Vector2f
    right_stick: Vector2f
    accel_left: Vector3f
    accel_right: Vector3f
    gyro_left: Gyro
    gyro_right: Gyro
    macro: bool

    def toStrArray(self):
        dl = self.gyro_left.direction
        dr = self.gyro_right.direction
        avl = self.gyro_left.ang_vel
        avr = self.gyro_right.ang_vel
        values = [self.step, self.buttons, self.left_stick.x, self.left_stick.y, self.right_stick.x, self.right_stick.y,
        self.accel_left.x, self.accel_left.y, self.accel_left.z, self.accel_right.x, self.accel_right.y, self.accel_right.z,
        dl.xx, dl.xy, dl.xz, dl.yx, dl.yy, dl.yz, dl.zx, dl.zy, dl.zz, avl.x, avl.y, avl.z,
        dr.xx, dr.xy, dr.xz, dr.yx, dr.yy, dr.yz, dr.zx, dr.zy, dr.zz, avr.x, avr.y, avr.z]
        return map(str, values)


@dataclass
class Script:
    change_stage_name:str
    change_stage_id:str
    scenario_no:int
    frame_count:int
    is_two_player:bool
    startPosition:Vector3f
    frames:list[Frame] = field(default_factory=list)


class Button(enum.Enum):
    cPadIdx_A = 0,
    cPadIdx_B = 1,
    cPadIdx_C = 2,
    cPadIdx_X = 3,
    cPadIdx_Y = 4,
    cPadIdx_Z = 5,
    cPadIdx_2 = 6, # R Stick Click
    cPadIdx_1 = 7,
    cPadIdx_Home = 8,
    cPadIdx_Minus = 9,
    cPadIdx_Plus = 10,
    cPadIdx_Start = 11,
    cPadIdx_Select = 12,
    cPadIdx_ZL = 2,
    cPadIdx_ZR = 5,
    cPadIdx_L = 13,
    cPadIdx_R = 14,
    cPadIdx_Touch = 15,
    cPadIdx_Up = 16,
    cPadIdx_Down = 17,
    cPadIdx_Left = 18,
    cPadIdx_Right = 19,
    cPadIdx_LeftStickUp = 20,
    cPadIdx_LeftStickDown = 21,
    cPadIdx_LeftStickLeft = 22,
    cPadIdx_LeftStickRight = 23,
    cPadIdx_rightUp = 24,
    cPadIdx_rightDown = 25,
    cPadIdx_rightLeft = 26,
    cPadIdx_rightRight = 27,
    cPadIdx_Max = 28

def to_f2(f4): #stores float with 2 byte precision if uncommented
    #return int(f4 * 32767) / 32767.0
    return f4

def getButtonBin(button):
    button = button.lower().strip()
    if button == "a": return 2**Button.cPadIdx_A.value[0]
    elif button == "b": return 2**Button.cPadIdx_B.value[0]
    elif button == "x": return 2**Button.cPadIdx_X.value[0]
    elif button == "y": return 2**Button.cPadIdx_Y.value[0]
    elif button == "l": return 2**Button.cPadIdx_L.value[0]
    elif button == "r": return 2**Button.cPadIdx_R.value[0]
    elif button == "zl": return 2**Button.cPadIdx_ZL.value[0]
    elif button == "zr": return 2**Button.cPadIdx_ZR.value[0]
    elif button == "plus" or button == "+": return 2**Button.cPadIdx_Plus.value[0]
    elif button == "minus" or button == "-": return 2**Button.cPadIdx_Minus.value[0]
    elif button == "dp-l": return 2**Button.cPadIdx_Left.value[0]
    elif button == "dp-u": return 2**Button.cPadIdx_Up.value[0]
    elif button == "dp-r": return 2**Button.cPadIdx_Right.value[0]
    elif button == "dp-d": return 2**Button.cPadIdx_Down.value[0]
    elif button == "ls": return 2**Button.cPadIdx_1.value[0]
    elif button == "rs": return 2**Button.cPadIdx_2.value[0]
    elif button == "ca": return 2**Button.cPadIdx_A.value[0]
    elif button == "cb": return 2**Button.cPadIdx_B.value[0]
    elif button == "cx": return 2**Button.cPadIdx_X.value[0]
    elif button == "cy": return 2**Button.cPadIdx_Y.value[0]
    elif button == "cl": return 2**Button.cPadIdx_L.value[0]
    elif button == "cr": return 2**Button.cPadIdx_R.value[0]
    elif button == "czl": return 2**Button.cPadIdx_ZL.value[0]
    elif button == "czr": return 2**Button.cPadIdx_ZR.value[0]
    elif button == "cplus" or button == "c+": return 2**Button.cPadIdx_Plus.value[0]
    elif button == "cminus" or button == "c-": return 2**Button.cPadIdx_Minus.value[0]
    elif button == "cdp-l": return 2**Button.cPadIdx_Left.value[0]
    elif button == "cdp-u": return 2**Button.cPadIdx_Up.value[0]
    elif button == "cdp-r": return 2**Button.cPadIdx_Right.value[0]
    elif button == "cdp-d": return 2**Button.cPadIdx_Down.value[0]
    elif button == "cls": return 2**Button.cPadIdx_1.value[0]
    elif button == "crs": return 2**Button.cPadIdx_2.value[0]
    else: return 0 #no button found

def prepareToken(token): #evaluates variables and math
    while match_obj := re.search("\\$\\w+", token): #replace variables with their values
        try:
            token = token.replace(match_obj.group(), vars.get(match_obj.group().lower()[1:]))
        except:
            print("Variable " + match_obj.group() + " not found")
            quit(-1)
    while match_obj := re.search("(-?[\\.0-9]+) *([+-]) *(-?[\\.0-9]+)", token): #evaluate math operations
        val_1 = float(match_obj.group(1))
        val_2 = float(match_obj.group(3))
        total = val_1
        if match_obj.group(2) == '+':
            total += val_2
        else:
            total -= val_2
        if total == int(total):
            total = int(total)
        token = token.replace(match_obj.group(0), str(total))
    
    frameOffset = 0 #handle frame offsets of the form [number]
    try:
        frameOffset = int(token[token.index('[') + 1 : token.index(']')])
        token = token.replace(token[token.index('[') : token.index(']') + 1], '')
    except:
        pass

    return token.lower(), frameOffset

def getStickPolar(token):
    r = 1.0
    theta = 0.0
    if ';' in token: #(r; theta)
        r = float(token[0:token.index(';')])
        theta = math.radians(float(token[token.index(';') + 1:]))
    else:# (r)
        theta = math.radians(float(token))
    return r, theta

def getStickCoordsFromPolar(r, theta):
    coords = Vector2f.zero()
    coords.x = int(32767 * r * math.cos(theta)) / 32767.0 #snap to nearest 2^16-representable float
    coords.y = int(32767 * r * math.sin(theta)) / 32767.0
    return coords

def getStickCoords(token):
    r, theta = getStickPolar(token)
    return getStickCoordsFromPolar(r, theta)

#euler in degrees to rotation matrix
def toRotationMatrix(euler:Vector3f):
    euler_radians = Vector3f.zero()
    euler_radians.x, euler_radians.y, euler_radians.z = math.radians(euler.x), math.radians(euler.y), math.radians(euler.z)

    cx = math.cos(euler_radians.x)
    cy = math.cos(euler_radians.y)
    cz = math.cos(euler_radians.z)
    sx = math.sin(euler_radians.x)
    sy = math.sin(euler_radians.y)
    sz = math.sin(euler_radians.z)
    
    return Matrix33f(to_f2(cy * cz), to_f2(-cy * sz), to_f2(sy), 
                                to_f2(cz * sx * sy + cx * sz), to_f2(cx * cz - sx * sy * sz), to_f2(-cy * sx),
                                to_f2(-cx * cz * sy + sx * sz), to_f2(cz * sx + cx * sy * sz), to_f2(cx * cy))

def getGyroValues(token):
    all = token.split(";") #(pitch; yaw; roll) or #(pitch; yaw; roll; ang-x; ang-y; ang-z)
    ang_vel = Vector3f.zero()
    euler = Vector3f.zero()
    if len(all) == 6:
        ang_vel.x, ang_vel.y, ang_vel.z = to_f2(float(all[3])), to_f2(float(all[4])), to_f2(float(all[5]))
    euler.x, euler.y, euler.z = float(all[0]), float(all[1]), float(all[2])
    
    return Gyro(euler, toRotationMatrix(euler), ang_vel)

def addToFrameRange(token, frameRange:range):
    try:
        doubling = 1
        rangeStart = -1
        for j in frameRange:
            if rangeStart < 0:
                rangeStart = j
        
        if "c" in token:

            if "(" in token: #stick/motion
                
                right = True #True if right stick/gyro/etc.
                left = True #True if left stick/gyro/etc.
                if "r" in token:
                    
                    left = False
                if "l" in token:
                    
                    right = False
                prefix = token[0:token.index('(')]
                token = token[token.index('(') + 1:token.index(')')]  

                if "s" in prefix: #stick
                    
                    if "x" in prefix:
                        coords = Vector2f.zero()
                        coords.x = int(token.split(";")[0])
                        coords.y = int(token.split(";")[1])
                    else:
                        coords = getStickCoords(token)
                    
                    for j in frameRange:
                        if right: script.frames[2*j+1].right_stick = coords
                        if left: script.frames[2*j+1].left_stick = coords
                
                elif "a" in prefix: #accelerometer
                    
                    accel = Vector3f(*map(to_f2, map(float, token.split(";"))))

                    for j in frameRange:
                        if right: script.frames[2*j+1].accel_right = accel
                        if left: script.frames[2*j+1].accel_left = accel
                
                elif "g" in prefix: #gyroscope
                    
                    gyro = getGyroValues(token)

                    for j in frameRange:
                        if right: script.frames[2*j+1].gyro_right = gyro
                        if left: script.frames[2*j+1].gyro_left = gyro

            elif "m" in token: #motion macros
                
                accel_left = Vector3f.default_accel()
                accel_right = Vector3f.default_accel()
                gyro_left = Gyro.zero()
                gyro_right = Gyro.zero()
                if token == "cm" or token == "cm-u":
                    accel_left = Vector3f(0, 3, 0)
                    gyro_left.ang_vel = Vector3f(-3, 0, 0)
                elif token == "cm-d":
                    accel_left = Vector3f(0, 3, 0)
                    gyro_left.ang_vel = Vector3f(3, 0, 0)
                elif token == "cm-l":
                    accel_left = Vector3f(-3, 0, 0)
                    gyro_left.ang_vel = Vector3f(0, 2, 0)
                elif token == "cm-r":
                    accel_left = Vector3f(3, 0, 0)
                    gyro_left.ang_vel = Vector3f(0, -2, 0)
                elif token == "cm-uu":
                    accel_left = accel_right = Vector3f(0, 3, 0)
                    gyro_left.ang_vel = gyro_right.ang_vel = Vector3f(-2, 0, 0)
                elif token == "cm-dd":
                    accel_left = accel_right = Vector3f(0, 3, 0)
                    gyro_left.ang_vel = gyro_right.ang_vel = Vector3f(2, 0, 0)
                elif token == "cm-ll":
                    accel_left = accel_right = Vector3f(-3, 0, 0)
                    gyro_left.ang_vel = gyro_right.ang_vel = Vector3f(0, 2, 0)
                elif token == "cm-rr":
                    accel_left = accel_right = Vector3f(3, 0, 0)
                    gyro_left.ang_vel = gyro_right.ang_vel = Vector3f(0, -2, 0)
                else:
                    return
                for j in frameRange:
                    script.frames[2*j+1].accel_left, script.frames[2*j+1].accel_right = accel_left, accel_right
                    script.frames[2*j+1].gyro_left, script.frames[2*j+1].gyro_right = gyro_left, gyro_right
                    script.frames[2*j+1].macro = True
                    
            else: #button or comment/invalid
                button_bin = getButtonBin(token)
                for j in frameRange:
                    if not (script.frames[2*j+1].buttons & button_bin):
                        script.frames[2*j+1].buttons += button_bin
            
        else:
            
            if "(" in token: #stick/motion
                right = True #True if right stick/gyro/etc.
                left = True #True if left stick/gyro/etc.
                if "r" in token:
                    left = False
                if "l" in token:
                    right = False
                prefix = token[0:token.index('(')]
                token = token[token.index('(') + 1:token.index(')')]  

                if "s" in prefix: #stick

                    if "x" in prefix:
                        coords = Vector2f.zero()
                        coords.x = int(token.split(";")[0])
                        coords.y = int(token.split(";")[1])
                    else:
                        coords = getStickCoords(token)
                    
                    for j in frameRange:
                        if right: script.frames[2*j].right_stick = coords
                        if left: script.frames[2*j].left_stick = coords
                
                elif "a" in prefix: #accelerometer
                    accel = Vector3f(*map(to_f2, map(float, token.split(";"))))

                    for j in frameRange:
                        if right: script.frames[2*j].accel_right = accel
                        if left: script.frames[2*j].accel_left = accel
                
                elif "g" in prefix: #gyroscope
                    gyro = getGyroValues(token)

                    for j in frameRange:
                        if right: script.frames[2*j].gyro_right = gyro
                        if left: script.frames[2*j].gyro_left = gyro

            elif "m" in token: #motion macros
                accel_left = Vector3f.default_accel()
                accel_right = Vector3f.default_accel()
                gyro_left = Gyro.zero()
                gyro_right = Gyro.zero()
                if token == "m" or token == "m-u":
                    accel_left = Vector3f(0, 3, 0)
                    gyro_left.ang_vel = Vector3f(-3, 0, 0)
                elif token == "m-d":
                    accel_left = Vector3f(0, 3, 0)
                    gyro_left.ang_vel = Vector3f(3, 0, 0)
                elif token == "m-l":
                    accel_left = Vector3f(-3, 0, 0)
                    gyro_left.ang_vel = Vector3f(0, 2, 0)
                elif token == "m-r":
                    accel_left = Vector3f(3, 0, 0)
                    gyro_left.ang_vel = Vector3f(0, -2, 0)
                elif token == "m-uu":
                    accel_left = accel_right = Vector3f(0, 3, 0)
                    gyro_left.ang_vel = gyro_right.ang_vel = Vector3f(-2, 0, 0)
                elif token == "m-dd":
                    accel_left = accel_right = Vector3f(0, 3, 0)
                    gyro_left.ang_vel = gyro_right.ang_vel = Vector3f(2, 0, 0)
                elif token == "m-ll":
                    accel_left = accel_right = Vector3f(-3, 0, 0)
                    gyro_left.ang_vel = gyro_right.ang_vel = Vector3f(0, 2, 0)
                elif token == "m-rr":
                    accel_left = accel_right = Vector3f(3, 0, 0)
                    gyro_left.ang_vel = gyro_right.ang_vel = Vector3f(0, -2, 0)
                else:
                    return
                
                for j in frameRange:
                    script.frames[2*j].accel_left, script.frames[2*j].accel_right = accel_left, accel_right
                    script.frames[2*j].gyro_left, script.frames[2*j].gyro_right = gyro_left, gyro_right
                    script.frames[2*j].macro = True
              
            else: #button or comment/invalid
                button_bin = getButtonBin(token)
                
                for j in frameRange:
                    if not (script.frames[2*j].buttons & button_bin):
                        script.frames[2*j].buttons += button_bin
            
    except:
        print("Syntax error(s) on line " + str(lineInNumber) + " prevented script generation")
        quit(-1)

def addInterpolatedStick(token, frameRange:range):
    try:
        token1, token2 = token.split("->")

        right = False #True if right stick/gyro/etc., False if left
        if "r" in token1:
            right = True
        
        token1 = token1[token1.index('(') + 1:token1.index(')')]
        token2 = token2[token2.index('(') + 1:token2.index(')')]

        r1, theta1 = getStickPolar(token1)
        r2, theta2 = getStickPolar(token2)

        dr = (r2 - r1) / (duration - 1)
        dtheta = (theta2 - theta1) / (duration - 1)

        r, theta = r1, theta1

        for i in range(frameRange.start, frameRange.stop - 1):
            if right:script.frames[i].right_stick = getStickCoordsFromPolar(r, theta)
            else:script.frames[i].left_stick = getStickCoordsFromPolar(r, theta)
            r += dr
            theta += dtheta
        if right:script.frames[frameRange.stop - 1].right_stick = getStickCoordsFromPolar(r2, theta2)
        else:script.frames[frameRange.stop - 1].left_stick = getStickCoordsFromPolar(r2, theta2)
    except:
        print("Syntax error(s) on line " + str(lineInNumber) + " prevented script generation")
        quit(-1)

stage_name = ""
entrance = ""
scenario = 1
is_two_player = False

script = Script(stage_name, entrance, scenario, -1, is_two_player, Vector3f.zero())

script.frame_count = 0

lineInNumber = 1

#count frames
with open(infile) as f:
    for lineIn in f:
        duration = 1
        first = lineIn.split(separator)[0]
        try:duration = int(first)
        except:
            if first == '':
                pass
            else:
                continue
        script.frame_count += duration
    f.close()
    
for i in range(script.frame_count):
    script.frames.append(Frame(i, False, 0, Vector2f.zero(), Vector2f.zero(), Vector3f.default_accel(), Vector3f.default_accel(), Gyro.zero(), Gyro.zero(), False))
    script.frames.append(Frame(i, True, 0, Vector2f.zero(), Vector2f.zero(), Vector3f.default_accel(), Vector3f.default_accel(), Gyro.zero(), Gyro.zero(), False))
    
indexStart = 0
indexStop = 0

vars = dict()

with open(infile) as f:
    for lineIn in f:
        lineIn = lineIn.split(separator)
        lineIn[-1] = lineIn[-1].strip()

        #handle first token (duration or variable assignment)
        duration = 1
        first = lineIn[0].strip()
        try:duration = int(first)
        except:
            if first == '':
                pass
            elif first[0] == '$' and '=' in first: #variables
                var = first[1:first.index('=')].strip().lower()
                value = first[first.index('=') + 1:].strip()

                #script start variables
                if var == 'stage':
                    script.change_stage_name = value
                elif var == 'entr' or var == 'entrance':
                    script.change_stage_id = value
                elif var == 'scen' or var == 'scenario':
                    try: script.scenario_no = int(value)
                    except:
                        print("Invalid scenario number")
                        quit(-1)
                elif var == 'independent_gyro' or var == 'ind_gyro':
                    if value.lower() == 'true' or value.lower() == 't':
                        independent_gyro = True
                elif var == 'pos' or var == 'position':
                    value = value[value.index('(') + 1:value.index(')')]
                    coords = value.split(';')
                    script.startPosition.x = float(coords[0])
                    script.startPosition.y = float(coords[1])
                    script.startPosition.z = float(coords[2])
                elif var == 'is2p' or var == 'is_two_player':
                    if value.lower() == 'true' or value.lower() == 't':
                        script.is_two_player = True
                        is_two_player = True
                #other variables
                else:
                    value = prepareToken(value)[0]
                    vars.update({var: value})
                lineInNumber += 1
                continue

            else:
                lineInNumber += 1
                continue
        
        indexStop = indexStart + duration
        for i in range(1, len(lineIn)):
            
            if lineIn[i] == '':
                continue

            is2p = False
            for k in lineIn:
                if "c" in k:
                    is2p = True

            token, indexOffset = prepareToken(lineIn[i])
            
            for i in range(script.frame_count, indexStop + indexOffset):
                script.frames.append(Frame(i, False, 0, Vector2f.zero(), Vector2f.zero(), Vector3f.zero(), Vector3f.zero(), Gyro.zero(), Gyro.zero(), False))
                if is2p:
                    script.frames.append(Frame(i, True, 0, Vector2f.zero(), Vector2f.zero(), Vector3f.zero(), Vector3f.zero(), Gyro.zero(), Gyro.zero(), False))
            script.frame_count = len(script.frames)
            if "->" in token: #stick interpolation
                addInterpolatedStick(token, range(indexStart + indexOffset, indexStop + indexOffset))

            elif "/" in token:
                steps = token.split('/')
                for i in range(len(steps)):
                    addToFrameRange(steps[i], range(indexStart + i + indexOffset, indexStop + indexOffset, len(steps)))

            else:
                if is2p:
                    addToFrameRange(token, range(indexStart + indexOffset, indexStop + indexOffset))
                else:
                    addToFrameRange(token, range(indexStart + indexOffset, indexStop + indexOffset))

        indexStart = indexStop
        lineInNumber += 1

    blankFrame = Frame(0, True, 0, Vector2f.zero(), Vector2f.zero(), Vector3f.default_accel(), Vector3f.default_accel(), Gyro.zero(), Gyro.zero(), False)

    #calculate angular velocity if gyroscope and angular velocity are not independent, or calculate proper gyroscope if a motion macro is used
    #angular velocity is change in gyroscope in degrees times -3/400
    if not independent_gyro:
        euler_left_old, euler_right_old = script.frames[0].gyro_left.euler, script.frames[0].gyro_right.euler 
        for i in range(1, script.frame_count):
            euler_left, euler_right = script.frames[i].gyro_left.euler, script.frames[i].gyro_right.euler
            if not script.frames[i].macro:
                script.frames[i].gyro_left.ang_vel = Vector3f(ANG_VEL_FACTOR*(euler_left.x - euler_left_old.x), ANG_VEL_FACTOR*(euler_left.y - euler_left_old.y), ANG_VEL_FACTOR*(euler_left.z - euler_left_old.z))
                script.frames[i].gyro_right.ang_vel = Vector3f(ANG_VEL_FACTOR*(euler_right.x - euler_right_old.x), ANG_VEL_FACTOR*(euler_right.y - euler_right_old.y), ANG_VEL_FACTOR*(euler_right.z - euler_right_old.z))
            '''
            else:
                ang_vel_left, ang_vel_right = script.frames[i].gyro_left.ang_vel, script.frames[i].gyro_right.ang_vel
                script.frames[i].gyro_left.euler = Vector3f(euler_left_old.x + ang_vel_left.x / ANG_VEL_FACTOR, euler_left_old.y + ang_vel_left.y / ANG_VEL_FACTOR, euler_left_old.z + ang_vel_left.z / ANG_VEL_FACTOR)
                script.frames[i].gyro_right.euler = Vector3f(euler_right_old.x + ang_vel_right.x / ANG_VEL_FACTOR, euler_right_old.y + ang_vel_right.y / ANG_VEL_FACTOR, euler_right_old.z + ang_vel_right.z / ANG_VEL_FACTOR)
                script.frames[i].gyro_left.direction = toRotationMatrix(script.frames[i].gyro_left.euler)
                script.frames[i].gyro_right.direction = toRotationMatrix(script.frames[i].gyro_right.euler)
            '''
            euler_left_old, euler_right_old = euler_left, euler_right

    #remove empty frames
    if (remove_empty):
        for i in range(script.frame_count - 1, -1, -1):
            blankFrame.step = i
            if blankFrame == script.frames[i]:
                del script.frames[i]

if debug:
    debugFile = open(outfile + "-debug.csv", "w")

    debugFile.write("Frame,Buttons,ls.x,ls.y,rs.x,rs.y,la.x,la.y,la.z,ra.x,ra.y,ra.z,lg.r.xx,lg.r.xy,lg.r.xz,lg.r.yx,lg.r.yy,lg.r.yz,lg.r.zx,lg.r.zy,lg.r.zz,lg.v.x,lg.v.y,lg.v.z,rg.r.xx,rg.r.xy,rg.r.xz,rg.r.yx,rg.r.yy,rg.r.yz,rg.r.zx,rg.r.zy,rg.r.zz,rg.v.x,rg.v.y,rg.v.z\n")
    for i in range(len(script.frames)):
        csv_writer = csv.writer(debugFile, delimiter = ',')
        data = script.frames[i].toStrArray()
        csv_writer.writerow(data)
    debugFile.close()

outf = open(outfile, "wb")

outf.write(b"BOOB")
outf.write(struct.pack("<I?3xi", len(script.frames), is_two_player, script.scenario_no))
outf.write(bytes(script.change_stage_name, encoding="ascii") + b'\0'*(128-len(script.change_stage_name)))
outf.write(bytes(script.change_stage_id, encoding="ascii") + b'\0'*(128-len(script.change_stage_id)))
outf.write(struct.pack("<3f", script.startPosition.x, script.startPosition.y, script.startPosition.z))

for frame in script.frames:
    outf.write(struct.pack("<I?3xI", frame.step, frame.second_player, frame.buttons))
    outf.write(struct.pack("<2f", frame.left_stick.x, frame.left_stick.y))
    outf.write(struct.pack("<2f", frame.right_stick.x, frame.right_stick.y))
    outf.write(struct.pack("<3f", frame.accel_left.x, frame.accel_left.y, frame.accel_left.z))
    outf.write(struct.pack("<3f", frame.accel_right.x, frame.accel_right.y, frame.accel_right.z))
    outf.write(struct.pack("<9f", frame.gyro_left.direction.xx, frame.gyro_left.direction.xy, frame.gyro_left.direction.xz, frame.gyro_left.direction.yx, frame.gyro_left.direction.yy, frame.gyro_left.direction.yz, frame.gyro_left.direction.zx, frame.gyro_left.direction.zy, frame.gyro_left.direction.zz))
    outf.write(struct.pack("<3f", frame.gyro_left.ang_vel.x, frame.gyro_left.ang_vel.y, frame.gyro_left.ang_vel.z))
    outf.write(struct.pack("<9f", frame.gyro_right.direction.xx, frame.gyro_right.direction.xy, frame.gyro_right.direction.xz, frame.gyro_right.direction.yx, frame.gyro_right.direction.yy, frame.gyro_right.direction.yz, frame.gyro_right.direction.zx, frame.gyro_right.direction.zy, frame.gyro_right.direction.zz))
    outf.write(struct.pack("<3f", frame.gyro_right.ang_vel.x, frame.gyro_right.ang_vel.y, frame.gyro_right.ang_vel.z))

outf.close()

print('Script successfully generated')

if ftp:
    ftp_config_file = open('ftp_config.json')
    ftp_config = json.load(ftp_config_file)
    ftp_config_file.close

    ftp = FTP()
    ftp.connect(host=ftp_config['ip'], port=int(ftp_config['port']))
    ftp.login(user=ftp_config['user'],passwd=ftp_config['passwd'])

    file = open(outfile, 'rb')

    result = ftp.storbinary('STOR SMO/tas/scripts/' + outfile, file)
    if result == '226 OK':
        print('Script successfully uploaded')
    else:
        print('FTP error')

    ftp.quit()
