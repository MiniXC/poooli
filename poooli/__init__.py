from PIL import Image, ImageOps, ImageEnhance
import ctypes
import binascii
import os

LZO = ctypes.cdll.LoadLibrary(os.getenv('MINILZO_PATH'))


class Poooli():
    INITIALIZE  = b"\x1b\x1cset mm\x05\x08"
    PAPER_WIDTH = b"\x10\x7e\x68\x79\x7a" + b"\xed\x09"
    BMP         = b"\x10\x7b\x3d\x3d"
    LINE_FEED   = b"\x16\x16\x0c\x57\x0d"
    WIDTH       = 384

    def __init__(self, socket=None):
        self.socket = socket

    def connect(self, mac, channel=1):
        self.socket.connect((mac, channel))
        self.socket.send(Poooli.INITIALIZE)
        self.socket.send(Poooli.PAPER_WIDTH)

    def process_image(self, file, mode="bnw_dither", contrast=1.0, brightness=1.0):
        image = Image.open(file).convert('RGBA')
        if brightness != 1.0:
            image = ImageEnhance.Brightness(image).enhance(brightness)
        if contrast != 1.0:
            image = ImageEnhance.Contrast(image).enhance(contrast)
        if image.width <= image.height:
            image = image.rotate(90, expand=True)
        image = image.resize(
            size=(
                Poooli.WIDTH, 
                int(image.height * Poooli.WIDTH / image.width)
            )
        )
        if mode == "bnw_dither":
            image = image.convert(mode="1")
        elif mode == "bnw":
            image = image.convert(mode="1", dither=Image.Dither.NONE)
        else:
            raise ValueError("Unknown mode: " + mode)
        return image

    def send_image(self, file, mode="bnw_dither", contrast=1.0, brightness=1.0):
        image = self.process_image(file, mode, contrast, brightness)
        work_memory = ctypes.create_string_buffer(16384 * 8)
        width_bytes = Poooli.WIDTH // 8
        for iy in range(image.height):
            image_bytes = b""
            for ix in range(width_bytes):
                byte = 0
                for bit in range(8):
                    if image.getpixel((ix * 8 + bit, iy)) == 0:
                        byte |= 1 << (7 - bit)
                image_bytes += byte.to_bytes(1, "little")
            lzo_image, lzono = Poooli.compress_to_lzo(image_bytes, work_memory, iy)
            self.socket.send(Poooli.BMP)
            self.socket.send((width_bytes  ^ (256 * 13 + 13)).to_bytes(2, "little"))
            self.socket.send((1 ^ (256 * 13 + 13)).to_bytes(2, "little"))
            self.socket.send(lzono)
            self.socket.send(lzo_image)
        self.socket.send(Poooli.LINE_FEED)

    @staticmethod
    def compress_to_lzo(image_bytes, wk, iy):
        buff = ctypes.create_string_buffer(image_bytes)   
        ni = ctypes.c_int(len(buff))
        no_max = len(buff) + len(buff) // 16 + 64 + 3
        out = ctypes.create_string_buffer(no_max) 
        no = ctypes.c_int(len(out))
        iret = LZO.lzo1x_1_compress(ctypes.byref(buff), ni, ctypes.byref(out), ctypes.byref(no), ctypes.byref(wk))
        lzno = no.value
        lzno_xor = lzno ^ (((13 * 256 + 13) * 256 + 13) * 256 + 13)
        lzno_xor = lzno_xor.to_bytes(4, "little")
        image_lzo = out[:lzno]
        image_lzo_xor = b""                                             # compressed data  
        for ib in range(no.value): 
            image_lzo_xor += (image_lzo[ib] ^ 13).to_bytes(1, "little")
        return image_lzo_xor, lzno_xor