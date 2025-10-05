# src/utils/firebase_utils.py
import firebase_admin
from firebase_admin import credentials, firestore

FIREBASE_CONFIG_PATH = "configs/firebaseConfig.json"
COLLECTION_NAME = "contacts"

def get_firestore_client():
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CONFIG_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def save_to_firestore(data_dict, key):
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(key)
    doc = doc_ref.get()

    if doc.exists:
        # Aqui você pode decidir se quer atualizar ou apenas logar
        print(f"Firestore: Data for key {key} already exists (skipping update).")
    else:
        doc_ref.set(data_dict)
        print(f"Firestore: Data for key {key} has been added.")