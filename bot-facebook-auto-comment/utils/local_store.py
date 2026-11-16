"""เก็บข้อมูลลับ (เช่น cookies ของ Facebook) ไว้ในเครื่องนี้เท่านั้น

- เก็บใน %LOCALAPPDATA%\\<ชื่อโปรแกรม>\\ ซึ่งไม่ซิงก์ขึ้น OneDrive และไม่ได้อยู่ในโฟลเดอร์โปรเจกต์
- บน Windows เข้ารหัสด้วย DPAPI: ไฟล์เปิดได้เฉพาะบัญชี Windows นี้บนเครื่องนี้
  ถ้าไฟล์ถูกก๊อปไปเครื่องอื่นหรือบัญชีอื่นจะถอดรหัสไม่ได้
"""
import json
import os

if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    _crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _blob_ptr = ctypes.POINTER(_DATA_BLOB)
    _crypt32.CryptProtectData.argtypes = [_blob_ptr, wintypes.LPCWSTR, _blob_ptr, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, _blob_ptr]
    _crypt32.CryptProtectData.restype = wintypes.BOOL
    _crypt32.CryptUnprotectData.argtypes = [_blob_ptr, ctypes.c_void_p, _blob_ptr, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, _blob_ptr]
    _crypt32.CryptUnprotectData.restype = wintypes.BOOL
    _kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    _kernel32.LocalFree.restype = ctypes.c_void_p
    _CRYPTPROTECT_UI_FORBIDDEN = 0x01

    def _dpapi(data, protect):
        buffer = ctypes.create_string_buffer(data, len(data))
        blob_in = _DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
        blob_out = _DATA_BLOB()
        if protect:
            ok = _crypt32.CryptProtectData(ctypes.byref(blob_in), "facebook-bot", None, None, None,
                                           _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out))
        else:
            ok = _crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None,
                                             _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out))
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            _kernel32.LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))


def data_dir(app_name):
    """โฟลเดอร์เก็บข้อมูลในเครื่องนี้ (สร้างให้ถ้ายังไม่มี)"""
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    path = os.path.join(base, app_name)
    os.makedirs(path, exist_ok=True)
    return path


def save_json(path, obj):
    """บันทึกข้อมูลแบบเข้ารหัส (เขียนไฟล์ชั่วคราวก่อน แล้วค่อยแทนที่ ไฟล์จะไม่เสียถ้าโปรแกรมปิดกลางคัน)"""
    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    data = _dpapi(raw, protect=True) if os.name == "nt" else raw
    temp_path = path + ".tmp"
    with open(temp_path, "wb") as file:
        file.write(data)
    if os.name != "nt":
        os.chmod(temp_path, 0o600)
    os.replace(temp_path, path)


def load_json(path):
    """อ่านข้อมูลที่บันทึกด้วย save_json"""
    with open(path, "rb") as file:
        data = file.read()
    raw = _dpapi(data, protect=False) if os.name == "nt" else data
    return json.loads(raw.decode("utf-8"))
