
import json
import os

import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


BASE_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "processed",
    "users"
)


def get_user_folder(user_id):
    if user_id is None or not str(user_id).isdigit():
        raise ValueError("Invalid user ID")

    folder = os.path.join(BASE_FOLDER, str(user_id))
    os.makedirs(folder, exist_ok=True)
    return folder


def get_user_files(user_id):
    folder = get_user_folder(user_id)

    return {
        "knowledge": os.path.join(folder, "knowledge_base.json"),
        "index": os.path.join(folder, "knowledge_base.index"),
        "metadata": os.path.join(folder, "faiss_metadata.json"),
        "vectorizer": os.path.join(folder, "tfidf_vectorizer.json"),
    }


def load_knowledge_base(user_id):
    files = get_user_files(user_id)

    if not os.path.exists(files["knowledge"]):
        return {"pdf": [], "ppt": [], "video": []}

    with open(files["knowledge"], "r", encoding="utf-8") as file:
        knowledge = json.load(file)

    knowledge.setdefault("pdf", [])
    knowledge.setdefault("ppt", [])
    knowledge.setdefault("video", [])

    return knowledge


def save_knowledge_base(
    pdf_data=None,
    ppt_data=None,
    video_data=None,
    user_id=None
):
    if user_id is None:
        raise ValueError("User login required")

    files = get_user_files(user_id)
    knowledge = load_knowledge_base(user_id)

    if pdf_data:
        knowledge["pdf"].extend(pdf_data)

    if ppt_data:
        knowledge["ppt"].extend(ppt_data)

    if video_data:
        knowledge["video"].extend(video_data)

    with open(files["knowledge"], "w", encoding="utf-8") as file:
        json.dump(knowledge, file, indent=2, ensure_ascii=False)

    build_faiss_index(knowledge, user_id)
    return knowledge


def build_faiss_index(knowledge, user_id):
    files = get_user_files(user_id)

    texts = []
    metadata = []

    for item in knowledge.get("pdf", []):
        text = str(item.get("text", "")).strip()
        if text:
            texts.append(text)
            metadata.append({
                "source": "PDF",
                "page": item.get("page"),
                "text": text
            })

    for item in knowledge.get("ppt", []):
        text = str(item.get("text", "")).strip()
        if text:
            texts.append(text)
            metadata.append({
                "source": "PPT",
                "slide": item.get("slide"),
                "text": text
            })

    for item in knowledge.get("video", []):
        text = str(item.get("text", "")).strip()
        if text:
            texts.append(text)
            metadata.append({
                "source": "VIDEO",
                "start": item.get("start"),
                "end": item.get("end"),
                "text": text
            })

    if not texts:
        for key in ("index", "metadata", "vectorizer"):
            if os.path.exists(files[key]):
                os.remove(files[key])
        return

    vectorizer = TfidfVectorizer(stop_words="english")
    vectors = vectorizer.fit_transform(texts).toarray().astype("float32")

    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(vectors)
    faiss.write_index(index, files["index"])

    with open(files["metadata"], "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2, ensure_ascii=False)

    vectorizer_data = {
        "vocabulary": vectorizer.vocabulary_,
        "idf": vectorizer.idf_.tolist()
    }

    with open(files["vectorizer"], "w", encoding="utf-8") as file:
        json.dump(vectorizer_data, file, indent=2)


def search_knowledge(query, top_k=5, user_id=None):
    if user_id is None:
        return []

    files = get_user_files(user_id)

    for key in ("index", "metadata", "vectorizer"):
        if not os.path.exists(files[key]):
            return []

    with open(files["metadata"], "r", encoding="utf-8") as file:
        metadata = json.load(file)

    with open(files["vectorizer"], "r", encoding="utf-8") as file:
        data = json.load(file)

    if not metadata:
        return []

    vectorizer = TfidfVectorizer(vocabulary=data["vocabulary"])
    vectorizer.idf_ = np.array(data["idf"], dtype="float64")

    query_vector = vectorizer.transform([query]).toarray().astype("float32")

    if not np.any(query_vector):
        return []

    index = faiss.read_index(files["index"])
    k = min(top_k, len(metadata))
    distances, indices = index.search(query_vector, k)

    similarities = 1 - distances[0] / 2
    top_similarity = float(similarities[0])

    if top_similarity < 0.05:
        return []

    threshold = max(0.05, top_similarity * 0.35)
    results = []

    for distance, similarity, number in zip(
        distances[0], similarities, indices[0]
    ):
        if number == -1 or similarity < threshold:
            continue

        result = metadata[number].copy()
        result["distance"] = float(distance)
        result["similarity"] = float(similarity)
        results.append(result)

    return results
