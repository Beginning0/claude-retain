"""claude-retain Plugin — Integración con claude-retain para Claude Code."""

__version__ = "0.1.1"

from .memory import MemoryManager
from .project_graph import ProjectGraphManager
from .graph_query import GraphQueryEngine
from .palace import get_collection, PalaceCollection
from .searcher import search_memories, index_document
from .layers import Layer0, Layer1, Layer2
from .entity_detector import detect_entities
from .knowledge_graph import KnowledgeGraph

