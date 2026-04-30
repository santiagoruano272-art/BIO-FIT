import logging
from datetime import datetime
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, firestore, auth

logger = logging.getLogger(__name__)

# Inicializar Firebase solo una vez (patrón singleton)
if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()


class FirebaseClient:
    """
    Encapsula todas las operaciones de lectura/escritura en Firebase.
    
    Colecciones en Firestore:
    - users/{uid}              → perfil del usuario
    - users/{uid}/routines/    → rutinas generadas
    - users/{uid}/chat_history → historial del asistente
    """

    # ── USUARIOS

    def get_user_profile(self, uid: str) -> dict | None:
        """Obtiene el perfil completo del usuario."""
        try:
            doc = db.collection('users').document(uid).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"Error obteniendo perfil de {uid}: {e}")
            return None

    def save_user_profile(self, uid: str, profile_data: dict) -> bool:
        """Crea o actualiza el perfil del usuario."""
        try:
            profile_data['updated_at'] = datetime.utcnow()
            db.collection('users').document(uid).set(profile_data, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error guardando perfil de {uid}: {e}")
            return False

    # ── RUTINAS

    def save_routine(self, user_id: str, routine_data: dict, user_inputs: dict) -> str:
        """
        Guarda una rutina generada en Firestore.
        
        Returns:
            str: ID del documento creado
        """
        try:
            doc_ref = db.collection('users').document(user_id)\
                         .collection('routines').document()
            
            doc_ref.set({
                'routine': routine_data,
                'user_inputs': user_inputs,
                'created_at': datetime.utcnow(),
                'is_active': True,
            })
            
            logger.info(f"Rutina guardada: {doc_ref.id} para usuario {user_id}")
            return doc_ref.id

        except Exception as e:
            logger.error(f"Error guardando rutina para {user_id}: {e}")
            raise

    def get_routine(self, user_id: str, routine_id: str) -> dict | None:
        """Obtiene una rutina específica por su ID."""
        try:
            doc = db.collection('users').document(user_id)\
                    .collection('routines').document(routine_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"Error obteniendo rutina {routine_id}: {e}")
            return None

    def get_user_routines(self, user_id: str, limit: int = 10) -> list:
        """Obtiene las rutinas del usuario, ordenadas por fecha."""
        try:
            docs = db.collection('users').document(user_id)\
                     .collection('routines')\
                     .order_by('created_at', direction=firestore.Query.DESCENDING)\
                     .limit(limit)\
                     .stream()
            
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]

        except Exception as e:
            logger.error(f"Error listando rutinas de {user_id}: {e}")
            return []

    def delete_routine(self, user_id: str, routine_id: str) -> bool:
        """Elimina una rutina del usuario."""
        try:
            db.collection('users').document(user_id)\
              .collection('routines').document(routine_id).delete()
            return True
        except Exception as e:
            logger.error(f"Error eliminando rutina {routine_id}: {e}")
            return False

    # ── Historial del asistente ─────────────────────────────

    def save_chat_history(self, user_id: str, session_id: str, history: list) -> bool:
        """Guarda el historial de chat del asistente."""
        try:
            db.collection('users').document(user_id)\
              .collection('chat_history').document(session_id).set({
                  'history': history,
                  'updated_at': datetime.utcnow(),
              }, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error guardando chat de {user_id}: {e}")
            return False

    def get_chat_history(self, user_id: str, session_id: str) -> list:
        """Obtiene el historial de chat de una sesión."""
        try:
            doc = db.collection('users').document(user_id)\
                    .collection('chat_history').document(session_id).get()
            if doc.exists:
                return doc.to_dict().get('history', [])
            return []
        except Exception as e:
            logger.error(f"Error obteniendo chat de {user_id}: {e}")
            return []


# ── Funciones de autenticación con Firebase Auth ─────────────

def verify_firebase_token(id_token: str) -> dict | None:
    """
    Verifica un token de Firebase Auth y devuelve los datos del usuario.
    Usado en el middleware de autenticación.
    """
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except auth.InvalidIdTokenError:
        logger.warning("Token de Firebase inválido")
        return None
    except auth.ExpiredIdTokenError:
        logger.warning("Token de Firebase expirado")
        return None
    except Exception as e:
        logger.error(f"Error verificando token Firebase: {e}")
        return None
