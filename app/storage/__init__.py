from app.storage.local import LocalStorage
from app.storage.swift import SwiftStorage


def create_storage(settings):
    if settings.storage_backend == "local":
        return LocalStorage(settings.storage_path)
    if settings.storage_backend == "swift":
        return SwiftStorage()
    raise ValueError("STORAGE_BACKEND must be local or swift")
