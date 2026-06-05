import logging
import json
import os
from datetime import datetime
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, firestore, auth

logger = logging.getLogger(__name__)

if not firebase_admin._apps:
    try:
        # Intentar cargar desde variable de entorno primero (para Render)
        firebase_creds_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
        if firebase_creds_json:
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
        else:
            # Fallback a archivo local (para desarrollo)
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        logger.warning(f"No se pudo inicializar Firebase Admin: {e}")

db = None
if firebase_admin._apps:
    db = firestore.client()

# ── CACHÉ EN MEMORIA PARA GIMNASIOS ──────────────────────────────────────────
# FIX: evita leer toda la colección en cada request de perfil.
# Se invalida automáticamente al crear/modificar un gimnasio.
_gyms_cache: list | None = None


def _invalidar_cache_gyms():
    global _gyms_cache
    _gyms_cache = None


class FirebaseClient:
    def __init__(self):
        self.db = db

    def _check_db(self):
        if not self.db:
            raise Exception("Firebase no está inicializado")

    # ── USUARIOS ──────────────────────────────────────────────────────────────

    def get_user_profile(self, uid: str) -> dict | None:
        if not self.db:
            return None
        try:
            doc = self.db.collection('users').document(uid).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error("Error obteniendo perfil de %s: %s", uid, e)
            return None

    def save_user_profile(self, uid: str, profile_data: dict) -> bool:
        if not self.db:
            return False
        try:
            profile_data['updated_at'] = datetime.utcnow()
            self.db.collection('users').document(uid).set(profile_data, merge=True)
            return True
        except Exception as e:
            logger.error("Error guardando perfil de %s: %s", uid, e)
            return False

    # ── RUTINAS ───────────────────────────────────────────────────────────────

    def save_routine(self, user_id: str, routine_data: dict, user_inputs: dict) -> str:
        self._check_db()
        try:
            doc_ref = (
                self.db.collection('users')
                .document(user_id)
                .collection('routines')
                .document()
            )
            doc_ref.set({
                'routine':     routine_data,
                'user_inputs': user_inputs,
                'created_at':  datetime.utcnow(),
                'is_active':   True,
            })
            return doc_ref.id
        except Exception as e:
            logger.error("Error guardando rutina para %s: %s", user_id, e)
            raise

    def get_user_routines(self, user_id: str, limit: int = 20) -> list:
        """
        Recupera las rutinas guardadas del usuario desde su subcolección
        users/{user_id}/routines/, ordenadas por fecha descendente.
        """
        if not self.db:
            return []
        try:
            docs = (
                self.db.collection('users')
                .document(user_id)
                .collection('routines')
                .order_by('created_at', direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error("Error obteniendo rutinas de %s: %s", user_id, e)
            return []

    # ── GIMNASIOS ─────────────────────────────────────────────────────────────

    def create_gym(self, data: dict) -> str:
        """Crea un gimnasio en la colección raíz y limpia el caché."""
        self._check_db()
        try:
            data['created_at'] = datetime.utcnow()
            doc_ref = self.db.collection('gimnasios').document()
            doc_ref.set(data)
            _invalidar_cache_gyms()          # FIX: invalida caché al crear
            logger.info("Gimnasio creado: %s", doc_ref.id)
            return doc_ref.id
        except Exception as e:
            logger.error("Error creando gimnasio: %s", e)
            raise

    def get_all_gyms(self) -> list:
        """
        Retorna todos los gimnasios registrados.
        FIX: usa caché en memoria para evitar lecturas repetidas a Firestore
        en cada request. Se invalida con _invalidar_cache_gyms().
        """
        global _gyms_cache
        if _gyms_cache is not None:
            return _gyms_cache
        if not self.db:
            return []
        try:
            docs = self.db.collection('gimnasios').stream()
            _gyms_cache = [{'id': doc.id, **doc.to_dict()} for doc in docs]
            return _gyms_cache
        except Exception as e:
            logger.error("Error listando gimnasios: %s", e)
            return []

    def get_gym_by_id(self, gym_id: str) -> dict | None:
        """
        FIX: método centralizado para buscar un gym por ID.
        Usa el caché de get_all_gyms() y también acepta gym_id como
        campo interno del documento (distinto del doc.id de Firestore).
        """
        gyms = self.get_all_gyms()
        for g in gyms:
            if g.get('id') == gym_id or g.get('gym_id') == gym_id:
                return g
        return None

    # ── EQUIPAMIENTOS (SUBCOLECCIÓN DE GIMNASIOS) ─────────────────────────────

    def _equip_collection(self, gym_id: str):
        self._check_db()
        return self.db.collection('gimnasios').document(gym_id).collection('equipamientos')

    def get_all_equipment(self, gym_id: str) -> list:
        if not self.db:
            return []
        try:
            docs = self._equip_collection(gym_id).stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error("Error obteniendo equipamiento del gimnasio %s: %s", gym_id, e)
            return []

    def create_equipment(self, gym_id: str, data: dict) -> str:
        self._check_db()
        try:
            data['created_at'] = datetime.utcnow()
            doc_ref = self._equip_collection(gym_id).document()
            doc_ref.set(data)
            return doc_ref.id
        except Exception as e:
            logger.error("Error agregando equipo al gimnasio %s: %s", gym_id, e)
            raise

    def update_equipment(self, gym_id: str, equip_id: str, data: dict) -> bool:
        self._check_db()
        try:
            doc_ref = self._equip_collection(gym_id).document(equip_id)
            data['updated_at'] = datetime.utcnow()
            doc_ref.update(data)
            return True
        except Exception as e:
            logger.error("Error actualizando equipo %s en gimnasio %s: %s", equip_id, gym_id, e)
            raise

    def delete_equipment(self, gym_id: str, equip_id: str) -> bool:
        self._check_db()
        try:
            self._equip_collection(gym_id).document(equip_id).delete()
            return True
        except Exception as e:
            logger.error("Error eliminando equipo %s en gimnasio %s: %s", equip_id, gym_id, e)
            raise


def verify_firebase_token(id_token: str) -> dict | None:
    if not firebase_admin._apps:
        return None
    try:
        return auth.verify_id_token(id_token)
    except Exception:
        return None