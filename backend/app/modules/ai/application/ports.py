"""Ports (interfaces) para el módulo AI."""

from abc import ABC, abstractmethod


class ILLMProvider(ABC):
    """Puerto: Proveedor de LLM (Ollama, OpenAI, etc)."""
    
    @abstractmethod
    async def generate(self, prompt: str, context: str = None) -> str:
        """Generar texto a partir de un prompt."""
        pass


class IVectorStore(ABC):
    """Puerto: Vector store para RAG (Qdrant, etc)."""
    
    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> list:
        """Buscar documentos similares."""
        pass
    
    @abstractmethod
    async def index(self, documents: list, metadata: dict) -> bool:
        """Indexar documentos."""
        pass


class IWebSearch(ABC):
    """Puerto: Búsqueda web (Tavily, Bing, etc)."""
    
    @abstractmethod
    async def search(self, query: str, max_results: int = 3) -> list:
        """Buscar en web."""
        pass
