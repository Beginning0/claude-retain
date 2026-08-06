"""
Entity Detector — Detección de entidades (personas, proyectos, archivos) desde texto.

Proporciona:
- detect_entities(): detectar entidades con scoring por similitud semántica

Dependencias: sentence-transformers (opcional, mejora calidad), regex (siempre)

Si sentence-transformers no está disponible, usa detección basada en regex como fallback.
"""

import os
import re
from typing import List, Dict, Optional, Any


def detect_entities(texts: List[Dict]) -> List[Dict]:
    """Detectar entidades en una lista de textos.

    Args:
        texts: Lista de dicts con keys "path" y "content"

    Returns:
        Lista de entidades detectadas con nombre, tipo y score
    """
    all_entities = []

    for text_item in texts:
        content = text_item.get("content", "")
        path = text_item.get("path", "?")

        # Detección por embeddings (mejor calidad)
        entities = _detect_with_embeddings(content, path)
        if entities:
            all_entities.extend(entities)
            continue  # Si hay embeddings, no usar regex

        # Fallback: detección por regex
        entities = _detect_with_regex(content, path)
        all_entities.extend(entities)

    # Deduplicar por nombre y tipo
    seen = set()
    unique = []
    for e in all_entities:
        key = (e["name"], e["type"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    # Ordenar por score descendente
    unique.sort(key=lambda x: x.get("score", 0), reverse=True)
    return unique


def _detect_with_embeddings(content: str, path: str = "") -> List[Dict]:
    """Detección de entidades con sentence-transformers (mejor calidad)."""
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")

        # Definir patrones de entidades para embedding comparison
        entity_patterns = {
            "person": [
                "John Smith", "Jane Doe", "developer", "programmer", "engineer",
                "architect", "designer", "manager", "CTO", "CEO", "CTO",
            ],
            "project": [
                "project", "repository", "codebase", "application", "service",
                "API", "frontend", "backend", "microservice", "pipeline",
            ],
            "file": [
                ".py", ".js", ".ts", ".tsx", ".jsx", ".css", ".html",
                ".json", ".yaml", ".yml", ".toml", ".md", ".txt",
            ],
        }

        # Detectar entidades por similitud semántica con patrones conocidos
        entities = []

        for entity_type, patterns in entity_patterns.items():
            for pattern in patterns:
                if pattern not in content:
                    continue

                # Calcular similitud entre el patrón y el contexto cercano
                idx = content.find(pattern)
                context_start = max(0, idx - 50)
                context_end = min(len(content), idx + len(pattern) + 50)
                context = content[context_start:context_end]

                # Embeddings de patrón y contexto
                pattern_embedding = model.encode(pattern)
                context_embedding = model.encode(context)

                # Cosine similarity
                similarity = float(
                    float(pattern_embedding.dot(context_embedding)) /
                    (float(pattern_embedding.norm()) * float(context_embedding.norm()))
                )

                if similarity > 0.4:  # Umbral de detección
                    entities.append({
                        "name": pattern,
                        "type": entity_type,
                        "score": round(similarity, 3),
                    })

        return entities if entities else None  # None significa "no encontrado"

    except ImportError:
        return None  # sentence-transformers no disponible


def _detect_with_regex(content: str, path: str = "") -> List[Dict]:
    """Detección de entidades por regex (fallback sin embeddings)."""
    entities = []

    # Detectar personas (nombres propios — mayúsculas seguidas de descripción)
    names = re.findall(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)\b', content)
    for name in names:
        entities.append({
            "name": name,
            "type": "person",
            "score": 0.9,
        })

    # Detectar nombres propios (palabras mayúsculas de 3+ letras no comunes)
    stop_words = {'EL', 'LA', 'LOS', 'LAS', 'UN', 'UNA', 'DE', 'DEL', 'EN', 'QUE', 'CON', 'POR', 'PARA', 'NO', 'SOB', 'TAM', 'MAS'}
    proper_names = [n for n in re.findall(r'\b([A-Z]{3,})\b', content) if n not in stop_words]
    for name in proper_names:
        entities.append({
            "name": name,
            "type": "project",
            "score": 0.7,
        })

    # Detectar nombres de archivos (extensión .py, .js, etc.)
    files = re.findall(r'\b(\w+\.\w+)\b', content)
    for f in files:
        entities.append({
            "name": f,
            "type": "file",
            "score": 0.6,
        })

    # Detectar nombres de variables/clases (camelCase o PascalCase seguidos de ":" o "(")
    classes = re.findall(r'\b([A-Z][a-z]+[A-Z]\w+)(?:\s*\(|:)', content)
    for cls in classes:
        entities.append({
            "name": cls,
            "type": "project",
            "score": 0.5,
        })

    return entities if entities else None  # None significa "no encontrado"
