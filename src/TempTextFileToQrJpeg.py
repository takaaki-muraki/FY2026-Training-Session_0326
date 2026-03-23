# -*- coding: utf-8 -*-
#
# TempTextFileToQrJpeg.py
#
# 目的:
#   temp テキストファイルを標準エディターで開き、
#   そこに入力されたテキスト(マルチライン可)から
#   QR コード(output.png / output.jpg)を作成する。
#
# 仕様:
#   ・入力方式以外は MultiLineInputTextToQrJpeg.py を踏襲する。
#   ・QR コード Version 40 + 誤り訂正 M の最大容量 2335 bytes を超えた場合、
#       何バイトオーバーかを cmd に表示して終了する。
#   ・生成した output.jpg を Paint で表示する。
#

import os
import subprocess
import tempfile
import pyqrcode
from PIL import Image


def main() -> None:
    # 出力ファイル
    pszOutputFile: str = "output.png"

    # JPEG出力ファイル
    pszJpegOutputFile: str = "output.jpg"

    # スケール
    iScale: int = 6

    # 誤り訂正レベル(M)。既存仕様そのまま。
    pszErrorLevel: str = "M"

    # Version 40 + M の最大バイト数
    iMaxBytes: int = 2335

    # temp 入力ファイル
    pszTempInputFile: str = os.path.join(tempfile.gettempdir(), "TempTextFileToQrJpeg_input.txt")

    # 入力用の初期ファイルを作成
    try:
        with open(pszTempInputFile, "w", encoding="utf-8") as pTmp:
            pTmp.write("ここにQRコードにしたい文字列を入力してください。\n入力後、保存してエディターを閉じてください。\n（この案内文は削除してから保存してください）\n")
    except Exception as objEx:
        with open("output_error.txt", "w", encoding="utf-8") as pErr:
            pErr.write(f"Error: unexpected exception while creating temp input file. Detail = {objEx}")
        return

    print(f"Please input text into this file, save, and close the editor: {pszTempInputFile}")

    # 標準エディターで temp ファイルを開いて、終了を待つ
    try:
        if os.name != "nt":
            raise RuntimeError("This script requires Windows to open the default editor via cmd.")
        subprocess.run(["cmd", "/c", "start", "", "/wait", pszTempInputFile], check=True)
    except Exception as objEx:
        with open("output_error.txt", "w", encoding="utf-8") as pErr:
            pErr.write(f"Error: unexpected exception while opening temp input file in default editor. Detail = {objEx}")
        return

    # エディターで保存された内容を読込
    try:
        with open(pszTempInputFile, "r", encoding="utf-8") as pTmp:
            pszTotalText: str = pTmp.read()
    except Exception as objEx:
        with open("output_error.txt", "w", encoding="utf-8") as pErr:
            pErr.write(f"Error: unexpected exception while reading temp input file. Detail = {objEx}")
        return

    # ================================
    # 追加仕様: バイト数チェック
    # ================================
    iByteCount: int = len(pszTotalText.encode("utf-8"))

    if iByteCount > iMaxBytes:
        iOver: int = iByteCount - iMaxBytes
        print(f"Error: input text is too large. {iOver} bytes over the QR limit ({iMaxBytes} bytes).")
        return

    # ================================
    # QR コード生成
    # ================================
    try:
        objQRCode: pyqrcode.QRCode = pyqrcode.create(
            content=pszTotalText,
            error=pszErrorLevel,
            version=None,
            mode=None,
            encoding="utf-8",
        )
    except Exception as objEx:
        with open("output_error.txt", "w", encoding="utf-8") as pErr:
            pErr.write(f"Error: unexpected exception while creating QR code. Detail = {objEx}")
        return

    # PNG 書込み
    try:
        objQRCode.png(pszOutputFile, scale=iScale)
    except Exception as objEx:
        with open("output_error.txt", "w", encoding="utf-8") as pErr:
            pErr.write(f"Error: unexpected exception while writing PNG file. Detail = {objEx}")
        return

    # ================================
    # 追加: PNG から JPEG を生成
    # ================================
    try:
        objImage: Image.Image = Image.open(pszOutputFile)
        objRgbImage: Image.Image = objImage.convert("RGB")
        objRgbImage.save(pszJpegOutputFile, format="JPEG")
    except Exception as objEx:
        with open("output_error.txt", "w", encoding="utf-8") as pErr:
            pErr.write(f"Error: unexpected exception while writing JPEG file. Detail = {objEx}")
        return

    # ================================
    # 追加: 生成した JPEG を Paint で表示
    # ================================
    try:
        pszJpegAbsPath: str = os.path.abspath(pszJpegOutputFile)
        subprocess.Popen(["mspaint", pszJpegAbsPath])
    except Exception as objEx:
        with open("output_error.txt", "w", encoding="utf-8") as pErr:
            pErr.write(f"Error: unexpected exception while opening JPEG file in Paint. Detail = {objEx}")
        return

    print(f"QR code output complete: {pszOutputFile} and {pszJpegOutputFile}")


if __name__ == "__main__":
    main()
