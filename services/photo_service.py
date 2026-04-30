from services.supabase_client import get_supabase, BUCKET
from services.utils import normalize_code

class PhotoService:
    def __init__(self):
        self.supabase = get_supabase()

    def upload_vehicle_photos(self, vehicle_code: str, files):
        vehicle_code = normalize_code(vehicle_code)
        uploaded = []
        for photo in files or []:
            file_path = f"vehicles/{vehicle_code.lower()}/{photo.name}"
            self.supabase.storage.from_(BUCKET).upload(
                file_path, photo.getvalue(), {"content-type": photo.type, "upsert": "true"}
            )
            public_url = self.supabase.storage.from_(BUCKET).get_public_url(file_path)
            row = {"vehicle_code": vehicle_code, "file_path": file_path, "public_url": public_url}
            self.supabase.table("vehicle_photos").insert(row).execute()
            uploaded.append(row)
        return uploaded

    def upload_item_photos(self, sku: str, files):
        sku = normalize_code(sku)
        uploaded = []
        for photo in files or []:
            file_path = f"items/{sku.lower()}/{photo.name}"
            self.supabase.storage.from_(BUCKET).upload(
                file_path, photo.getvalue(), {"content-type": photo.type, "upsert": "true"}
            )
            public_url = self.supabase.storage.from_(BUCKET).get_public_url(file_path)
            row = {
                "sku": sku,
                "file_path": file_path,
                "public_url": public_url,
                "photo_type": self.guess_photo_type(photo.name),
            }
            self.supabase.table("item_photos").insert(row).execute()
            uploaded.append(row)
        return uploaded

    def guess_photo_type(self, file_name: str) -> str:
        name = file_name.lower()
        if "front" in name:
            return "front"
        if "back" in name:
            return "back"
        if "label" in name or "oem" in name or "tag" in name:
            return "label"
        if "damage" in name or "wear" in name:
            return "damage"
        return "general"

    def get_vehicle_photos(self, vehicle_code: str):
        return self.supabase.table("vehicle_photos").select("*").eq(
            "vehicle_code", normalize_code(vehicle_code)
        ).execute().data

    def get_item_photos(self, sku: str):
        return self.supabase.table("item_photos").select("*").eq(
            "sku", normalize_code(sku)
        ).execute().data
