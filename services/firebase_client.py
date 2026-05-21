import logging
from datetime import datetime
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, firestore, auth

logger = logging.getLogger(__name__)

if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()


class FirebaseClient:
    def __init__(self):
        self.db = db

    # ── USUARIOS ─────────────────────────────────────────────────────────────

    def get_user_profile(self, uid: str) -> dict | None:
        try:
            doc = db.collection('users').document(uid).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"Error obteniendo perfil de {uid}: {e}")
            return None

    def save_user_profile(self, uid: str, profile_data: dict) -> bool:
        try:
            profile_data['updated_at'] = datetime.utcnow()
            db.collection('users').document(uid).set(profile_data, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error guardando perfil de {uid}: {e}")
            return False

    # ── RUTINAS ───────────────────────────────────────────────────────────────

    def save_routine(self, user_id: str, routine_data: dict, user_inputs: dict) -> str:
        try:
            doc_ref = db.collection('users').document(user_id).collection('routines').document()
            doc_ref.set({
                'routine':     routine_data,
                'user_inputs': user_inputs,
                'created_at':  datetime.utcnow(),
                'is_active':   True,
            })
            return doc_ref.id
        except Exception as e:
            logger.error(f"Error guardando rutina para {user_id}: {e}")
            raise

    # ── GIMNASIOS (NUEVA COLECCIÓN PRINCIPAL) ──────────────────────────────────

    def create_gym(self, data: dict) -> str:
        """Crea un gimnasio en la colección raíz principal."""
        try:
            data['created_at'] = datetime.utcnow()
            doc_ref = db.collection('gimnasios').document()
            doc_ref.set(data)
            logger.info(f"Gimnasio creado exitosamente con ID: {doc_ref.id}")
            return doc_ref.id
        except Exception as e:
            logger.error(f"Error creando gimnasio: {e}")
            raise

    def get_all_gyms(self) -> list:
        """Retorna todos los gimnasios registrados."""
        try:
            docs = db.collection('gimnasios').stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"Error listando gimnasios: {e}")
            return []

    # ── EQUIPAMIENTOS (REESTRUCTURADO COMO SUBCOLECCIÓN DE GIMNASIOS) ──────────

    def _equip_collection(self, gym_id: str):
        """Referencia a la sub-colección interna de equipamientos dentro de un gimnasio."""
        return db.collection('gimnasios').document(gym_id).collection('equipamientos')

    def get_all_equipment(self, gym_id: str) -> list:
        """Trae los equipamientos de la subcolección interna del gimnasio dado."""
        try:
            docs = self._equip_collection(gym_id).stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"Error obteniendo equipamiento del gimnasio {gym_id}: {e}")
            return []

    def create_equipment(self, gym_id: str, data: dict) -> str:
        """Inserta un equipamiento dentro de la subcolección del gimnasio correspondiente."""
        try:
            data['created_at'] = datetime.utcnow()
            doc_ref = self._equip_collection(gym_id).document()
            doc_ref.set(data)
            return doc_ref.id
        except Exception as e:
            logger.error(f"Error agregando equipo al gimnasio {gym_id}: {e}")
            raise

    def update_equipment(self, gym_id: str, equip_id: str, data: dict) -> bool:
        try:
            doc_ref = self._equip_collection(gym_id).document(equip_id)
            data['updated_at'] = datetime.utcnow()
            doc_ref.update(data)
            return True
        except Exception as e:
            logger.error(f"Error actualizando equipo {equip_id} en gimnasio {gym_id}: {e}")
            raise

    def delete_equipment(self, gym_id: str, equip_id: str) -> bool:
        try:
            self._equip_collection(gym_id).document(equip_id).delete()
            return True
        except Exception as e:
            logger.error(f"Error eliminando equipo {equip_id} en gimnasio {gym_id}: {e}")
            raise


def verify_firebase_token(id_token: str) -> dict | None:
    try:
        return auth.verify_id_token(id_token)
    except Exception:
        return None