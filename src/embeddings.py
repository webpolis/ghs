from sentence_transformers import SentenceTransformer
from typing import List, Optional
import numpy as np


class EmbeddingGenerator:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding generator with a lightweight model.
        Default model 'all-MiniLM-L6-v2' is ~80MB and produces 384-dimensional embeddings.
        """
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    def generate_embedding(
        self,
        title: str,
        description: Optional[str],
        readme: Optional[str]
    ) -> List[float]:
        """
        Generate embedding from repository metadata.
        Combines title, description, and README content (truncated).
        """
        parts = [title]

        if description:
            parts.append(description)

        if readme:
            truncated_readme = readme[:5000]
            parts.append(truncated_readme)

        combined_text = " | ".join(parts)

        embedding = self.model.encode(combined_text, convert_to_numpy=True)

        return embedding.tolist()

    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        """
        embedding = self.model.encode(query, convert_to_numpy=True)
        return embedding.tolist()

    def get_embedding_dimension(self) -> int:
        """
        Return the dimension of the embeddings produced by this model.
        """
        return self.embedding_dim
