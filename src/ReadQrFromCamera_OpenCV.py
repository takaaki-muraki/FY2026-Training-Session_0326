# -*- coding: utf-8 -*-
#
# ReadQrFromCamera_Pyzbar.py
#
# 目的:
#   PC のカメラから QR コードを読み取り、
#   1) ログファイルへ追記保存
#   2) 1件ごとに別ファイルを作成し、標準エディタで自動的に開く
#   を行う。
#
# 特徴:
#   ・カメラ映像の取得は OpenCV(cv2)
#   ・QR コードのデコードは pyzbar
#   ・pyzbar が返す「生バイト列」に対して
#       UTF-8 → 失敗したら cp932(Shift-JIS) の順で decode を試みる
#   ・同じ内容の QR を短時間に何度も読み取っても、連続起動しないように制御する
#

import sys
import os
from datetime import datetime
from typing import Optional, Any, List

import cv2
from pyzbar import pyzbar


# -------------------------------------------------------------
# エラーメッセージをテキストファイルへ書き込む
# -------------------------------------------------------------
def write_error_text(pszFilePath: str, pszMessage: str) -> None:
    """
    pszFilePath で指定されたパスに、pszMessage を UTF-8 で書き込む。
    既存ファイルがある場合は上書きする。
    """
    with open(pszFilePath, "w", encoding="utf-8") as pFile:
        pFile.write(pszMessage)


# -------------------------------------------------------------
# ログファイルへ結果を 1 行追記する
# -------------------------------------------------------------
def append_result_text(pszFilePath: str, pszDecoded: str) -> None:
    """
    ログファイルに
        YYYY-MM-DD HH:MM:SS<TAB>decoded_text
    の形式で 1 行追記する。
    """
    objNow: datetime = datetime.now()
    pszTime: str = objNow.strftime("%Y-%m-%d %H:%M:%S")
    with open(pszFilePath, "a", encoding="utf-8") as pFile:
        pFile.write(f"{pszTime}\t{pszDecoded}\n")


# -------------------------------------------------------------
# 1件専用ファイルを作成し、標準エディタで開く
# -------------------------------------------------------------
def write_single_file_and_open(pszDir: str, pszDecoded: str) -> None:
    """
    ログ用とは別に、1件ごとのテキストファイルを作成して標準エディタで開く。

    仕様(ユーザー指定):
      ・このスクリプト(ReadQrFromCamera_OpenCV.py)があるフォルダー直下に Output フォルダーを作成
        (既にある場合は作成しない)
      ・Output フォルダー下に、次のファイル名で保存する
          qr_contents_yyyy年mm月dd日_hh時mm分ss秒.txt
      ・内容は QR 解読結果を保存し、最後に改行(\n)を1つ追加する
      ・保存後、標準のエディタで該当ファイルを開く
    """
    try:
        pszScriptDir: str = os.path.dirname(os.path.abspath(__file__))
        pszOutputDir: str = os.path.join(pszScriptDir, "Output")
        os.makedirs(pszOutputDir, exist_ok=True)

        objNow: datetime = datetime.now()
        pszName: str = objNow.strftime("qr_contents_%Y年%m月%d日_%H時%M分%S秒.txt")
        pszFull: str = os.path.join(pszOutputDir, pszName)

        # 最後に改行(\n)を1つ追加して保存する
        pszBody: str = pszDecoded.rstrip("\n") + "\n"
        with open(pszFull, "w", encoding="utf-8") as pFile:
            pFile.write(pszBody)

        # 標準エディタで開く
        os.startfile(pszFull)

    except Exception as objEx:
        write_error_text(
            "ReadQrFromCamera_Pyzbar_error_single_open.txt",
            f"Error: failed to write/open single file. Detail = {objEx}",
        )


# -------------------------------------------------------------
# 生バイト列を UTF-8 / cp932 の順で decode する
# -------------------------------------------------------------
def decode_bytes_auto(pszRaw: bytes) -> Optional[str]:
    """
    pyzbar から得られた生バイト列をテキストに変換する。

    優先順位:
      1) UTF-8
      2) cp932(Shift-JIS)
    の順で decode を試みる。

    どちらでも失敗した場合は:
      ・エラーファイル ReadQrFromCamera_Pyzbar_error_unicode.txt に詳細を書き出す
      ・標準出力に Warning を表示する
      ・戻り値 None を返す
    """
    # まず UTF-8 で試す
    try:
        pszText: str = pszRaw.decode("utf-8")
        return pszText
    except UnicodeDecodeError:
        pass

    # 次に cp932(Shift-JIS) で試す
    try:
        pszText = pszRaw.decode("cp932")
        return pszText
    except UnicodeDecodeError as objEx:
        # UTF-8 でも cp932 でも解釈できなかった場合はエラーを記録
        pszHex: str = pszRaw.hex()
        pszMsg: str = (
            "Error: failed to decode QR data as UTF-8 and cp932.\n"
            f"Detail = {objEx}\n"
            f"RawHex = {pszHex}\n"
        )
        write_error_text("ReadQrFromCamera_Pyzbar_error_unicode.txt", pszMsg)
        print("Warning: failed to decode QR data as UTF-8 and cp932.")
        return None


# -------------------------------------------------------------
# カメラループ本体
# -------------------------------------------------------------
def run_camera_loop(pszOutputFile: str) -> None:
    """
    カメラからフレームを取得し、pyzbar で QR コードを読み取るメインループ。

    機能:
      ・pyzbar.decode で取得した生バイト列を decode_bytes_auto で文字列化
      ・同じ内容の QR コードを短時間に何度も処理しない
      ・結果をログファイルへ追記
      ・1件ごとに別ファイルを作成し標準エディタで開く
      ・q キーで終了
    """
    # 出力先ディレクトリを取得（引数がファイル名のみの場合、カレントディレクトリ）
    pszDir: str = os.path.dirname(pszOutputFile)
    if pszDir == "":
        pszDir = os.getcwd()

    # カメラをオープン（0 はデフォルトカメラ）
    objCap: cv2.VideoCapture = cv2.VideoCapture(0)

    # カメラが開けない場合はエラーにして終了
    if not objCap.isOpened():
        write_error_text(
            "ReadQrFromCamera_Pyzbar_error_camera.txt",
            "Error: failed to open camera.",
        )
        print("Error: failed to open camera.")
        return

    print("Press q to quit.")  # カメラプレビューの終了キー案内

    # 最後に処理した QR の内容と、その時刻
    pszLastDecoded: str = ""
    objLastWriteTime: Optional[datetime] = None

    # 同じ内容を再処理するまでの最低待ち秒数
    iMinIntervalSeconds: int = 2

    while True:
        # カメラからフレームを取得
        bRet: bool
        objFrame: Any
        bRet, objFrame = objCap.read()

        if not bRet:
            # フレームが読めなければエラーで終了
            write_error_text(
                "ReadQrFromCamera_Pyzbar_error_camera.txt",
                "Error: failed to read frame.",
            )
            print("Error: failed to read frame.")
            break

        # pyzbar で QR コードを検出・デコード
        objCodes: List[Any] = pyzbar.decode(objFrame)

        # フレーム内に複数の QR がある場合は、1件ずつ処理する
        for objCode in objCodes:
            # 生バイト列を取得
            pszRaw: bytes = objCode.data

            # UTF-8 / cp932 の順で decode を試みる
            pszDecoded: Optional[str] = decode_bytes_auto(pszRaw)

            # どちらの decode にも失敗した場合は、この QR はスキップ
            if pszDecoded is None:
                continue

            # 今回の内容を処理するかどうかを判定
            objNow: datetime = datetime.now()
            bShouldProcess: bool = False

            # 1) 内容が前回と違う場合は必ず処理
            if pszDecoded != pszLastDecoded:
                bShouldProcess = True
            else:
                # 2) 内容が同じ場合は、前回からの経過秒数を見る
                if objLastWriteTime is None:
                    bShouldProcess = True
                else:
                    fDiffSeconds: float = (
                        objNow - objLastWriteTime
                    ).total_seconds()
                    if fDiffSeconds >= iMinIntervalSeconds:
                        bShouldProcess = True

            if bShouldProcess:
                # ログファイルへ追記
                try:
                    append_result_text(pszOutputFile, pszDecoded)
                except Exception as objEx:
                    write_error_text(
                        "ReadQrFromCamera_Pyzbar_error_write.txt",
                        f"Error: unexpected exception while writing result file. Detail = {objEx}",
                    )

                # 1件専用ファイルを作成し、標準エディタで開く
                try:
                    write_single_file_and_open(pszDir, pszDecoded)
                except Exception as objEx:
                    write_error_text(
                        "ReadQrFromCamera_Pyzbar_error_single_write.txt",
                        f"Error: failed to write single file. Detail = {objEx}",
                    )

                # 最後に処理した内容と時刻を更新
                pszLastDecoded = pszDecoded
                objLastWriteTime = objNow

        # カメラ映像を表示
        cv2.imshow("ReadQrFromCamera_Pyzbar", objFrame)

        # q キーを押したら終了
        iKey: int = cv2.waitKey(1)
        if iKey == ord("q"):
            break

    # 終了処理
    objCap.release()
    cv2.destroyAllWindows()


# -------------------------------------------------------------
# メインエントリポイント
# -------------------------------------------------------------
def main() -> None:
    """
    コマンドライン引数を解釈し、ログファイルパスを決定して
    run_camera_loop を呼び出す。
    """
    iArgCount: int = len(sys.argv)

    if iArgCount == 1:
        # 引数なし → カレントディレクトリに既定ファイル名で保存
        pszOutputFile: str = os.path.join(
            os.getcwd(), "ReadQrFromCamera_Pyzbar_result.txt"
        )
    elif iArgCount == 2:
        # 引数1個 → 指定されたパスをそのまま使用
        pszOutputFile = sys.argv[1]
        pszDir: str = os.path.dirname(pszOutputFile)

        # ディレクトリが存在しない場合は作成を試みる
        if pszDir != "" and not os.path.isdir(pszDir):
            try:
                os.makedirs(pszDir, exist_ok=True)
            except Exception as objEx:
                write_error_text(
                    "ReadQrFromCamera_Pyzbar_error_argument.txt",
                    f"Error: failed to create directory. Detail = {objEx}",
                )
                print("Error: failed to create directory.")
                return
    else:
        # 引数が多すぎる場合はエラーとして終了
        pszErr: str = (
            "Error: too many arguments.\n"
            "Usage: python ReadQrFromCamera_Pyzbar.py [output_text_file_path]\n"
            "Example: python ReadQrFromCamera_Pyzbar.py C:\\Data\\qr_log_pyzbar.txt\n"
        )
        write_error_text("ReadQrFromCamera_Pyzbar_error_argument.txt", pszErr)
        print(pszErr)
        return

    # カメラループ開始
    run_camera_loop(pszOutputFile)


if __name__ == "__main__":
    main()
