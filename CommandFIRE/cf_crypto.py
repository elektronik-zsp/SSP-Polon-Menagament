"""CommandFIRE CFDB v1; AES-256-GCM. Requires cryptography >= 42.
The key is never placed in the shared folder. Windows DPAPI protects a per-user local copy.
"""
import os, struct
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
MAGIC = b'CFDB\x01'
AAD = b'CommandFIRE SSP Serwis CFDB v1'

def encrypt(raw, key):
    if len(key) != 32: raise ValueError('Nieprawidlowa dlugosc klucza.')
    nonce = os.urandom(12)
    return MAGIC + nonce + AESGCM(key).encrypt(nonce, raw, AAD)

def decrypt(raw, key):
    if not raw.startswith(MAGIC) or len(raw) < len(MAGIC)+12+16:
        raise ValueError('Nieprawidlowy plik CFDB.')
    nonce = raw[len(MAGIC):len(MAGIC)+12]
    try: return AESGCM(key).decrypt(nonce, raw[len(MAGIC)+12:], AAD)
    except Exception as exc: raise ValueError('Nie mozna odszyfrowac bazy: zly klucz lub uszkodzony plik.') from exc

def protect_windows(data):
    if os.name != 'nt': raise OSError('DPAPI wymaga Windows.')
    import ctypes
    from ctypes import wintypes
    class BLOB(ctypes.Structure):
        _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]
    source=ctypes.create_string_buffer(data)
    inp=BLOB(len(data),ctypes.cast(source,ctypes.POINTER(ctypes.c_ubyte)))
    dest=BLOB()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True)
    crypt.CryptProtectData.argtypes=[ctypes.POINTER(BLOB),wintypes.LPCWSTR,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(BLOB)]
    crypt.CryptProtectData.restype=wintypes.BOOL
    if not crypt.CryptProtectData(ctypes.byref(inp),'CommandFIRE CFDB key',None,None,None,1,ctypes.byref(dest)):
        raise ctypes.WinError(ctypes.get_last_error())
    try: return ctypes.string_at(dest.pbData,dest.cbData)
    finally:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        kernel.LocalFree(dest.pbData)

def unprotect_windows(data):
    if os.name != 'nt': raise OSError('DPAPI wymaga Windows.')
    import ctypes
    from ctypes import wintypes
    class BLOB(ctypes.Structure):
        _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]
    source=ctypes.create_string_buffer(data)
    inp=BLOB(len(data),ctypes.cast(source,ctypes.POINTER(ctypes.c_ubyte)))
    dest=BLOB()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True)
    crypt.CryptUnprotectData.argtypes=[ctypes.POINTER(BLOB),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(BLOB)]
    crypt.CryptUnprotectData.restype=wintypes.BOOL
    if not crypt.CryptUnprotectData(ctypes.byref(inp),None,None,None,None,1,ctypes.byref(dest)):
        raise ctypes.WinError(ctypes.get_last_error())
    try: return ctypes.string_at(dest.pbData,dest.cbData)
    finally:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        kernel.LocalFree(dest.pbData)
