"""
LangChain and LlamaIndex integrations.
"""
import json
from typing import List, Dict, Any, Optional
from loguru import logger


class LangChainLoader:
    """
    LangChain document loader for scraped content.
    """

    def __init__(self):
        self.langchain_available = self._check_langchain()
        self.llamaindex_available = self._check_llamaindex()

    def _check_langchain(self) -> bool:
        try:
            from langchain_community.document_loaders import WebBaseLoader
            return True
        except ImportError:
            logger.warning("LangChain not installed")
            return False

    def _check_llamaindex(self) -> bool:
        try:
            import llama_index
            return True
        except ImportError:
            logger.warning("LlamaIndex not installed")
            return False

    def load_langchain(self, url: str, selectors: Dict[str, str] = None) -> List:
        """Load scraped content into LangChain documents."""
        if not self.langchain_available:
            return []

        try:
            from langchain_community.document_loaders import WebBaseLoader
            from langchain.schema import Document

            if selectors:
                # Use custom extraction
                loader = WebBaseLoader(url)
                docs = loader.load()

                # Filter to selected content
                filtered = []
                for doc in docs:
                    # Simple text content - in production would parse selectors
                    filtered.append(Document(
                        page_content=doc.page_content[:5000],
                        metadata={**doc.metadata, "url": url}
                    ))
                return filtered
            else:
                loader = WebBaseLoader(url)
                return loader.load()

        except Exception as e:
            logger.error(f"LangChain load failed: {e}")
            return []

    def create_langchain_chain(self, docs: List) -> Any:
        """Create a LangChain chain for Q&A."""
        if not self.langchain_available:
            return None

        try:
            from langchain_openai import ChatOpenAI
            from langchain.chains import RetrievalQA
            from langchain.vectorstores import FAISS
            from langchain.embeddings import OpenAIEmbeddings

            # Create vector store
            embeddings = OpenAIEmbeddings()
            vectorstore = FAISS.from_documents(docs, embeddings)

            # Create chain
            llm = ChatOpenAI()
            chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=vectorstore.as_retriever()
            )

            return chain

        except Exception as e:
            logger.error(f"LangChain chain creation failed: {e}")
            return None

    def load_llamaindex(self, docs: List[Dict]) -> Any:
        """Load scraped content into LlamaIndex."""
        if not self.llamaindex_available:
            return None

        try:
            from llama_index import Document, VectorStoreIndex

            # Convert to LlamaIndex documents
            llama_docs = []
            for doc in docs:
                if isinstance(doc, dict):
                    text = doc.get("text", "")
                    metadata = {k: v for k, v in doc.items() if k != "text"}
                    llama_docs.append(Document(text=text, metadata=metadata))
                else:
                    llama_docs.append(Document(text=str(doc)))

            # Create index
            index = VectorStoreIndex.from_documents(llama_docs)
            return index

        except Exception as e:
            logger.error(f"LlamaIndex load failed: {e}")
            return None

    def query_llamaindex(self, index: Any, query: str) -> str:
        """Query LlamaIndex."""
        if not index:
            return ""

        try:
            query_engine = index.as_query_engine()
            response = query_engine.query(query)
            return str(response)

        except Exception as e:
            logger.error(f"LlamaIndex query failed: {e}")
            return ""


class ScrapedDocument:
    """Wrapper for scraped documents with metadata."""

    def __init__(self, content: str, metadata: Dict[str, Any] = None):
        self.content = content
        self.metadata = metadata or {}

    def to_langchain(self):
        """Convert to LangChain document."""
        try:
            from langchain.schema import Document
            return Document(
                page_content=self.content,
                metadata=self.metadata
            )
        except:
            return None

    def to_llamaindex(self):
        """Convert to LlamaIndex document."""
        try:
            from llama_index import Document
            return Document(
                text=self.content,
                metadata=self.metadata
            )
        except:
            return None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "metadata": self.metadata
        }


class MultiFormatExporter:
    """Export scraped data to multiple formats."""

    @staticmethod
    def to_langchain(docs: List[Dict]) -> List:
        """Convert to LangChain documents."""
        from langchain.schema import Document

        result = []
        for doc in docs:
            result.append(Document(
                page_content=doc.get("content", ""),
                metadata=doc.get("metadata", {})
            ))
        return result

    @staticmethod
    def to_llamaindex(docs: List[Dict]):
        """Convert to LlamaIndex documents."""
        try:
            from llama_index import Document

            result = []
            for doc in docs:
                result.append(Document(
                    text=doc.get("content", ""),
                    metadata=doc.get("metadata", {})
                ))
            return result
        except:
            return None

    @staticmethod
    def to_json(docs: List[Dict]) -> str:
        """Convert to JSON."""
        return json.dumps(docs, indent=2, default=str)

    @staticmethod
    def to_markdown(docs: List[Dict]) -> str:
        """Convert to Markdown."""
        lines = []
        for i, doc in enumerate(docs):
            lines.append(f"## Document {i + 1}\n")
            if doc.get("metadata"):
                lines.append("### Metadata\n")
                for k, v in doc.get("metadata", {}).items():
                    lines.append(f"- **{k}**: {v}")
                lines.append("")
            lines.append(doc.get("content", ""))
            lines.append("\n---\n")
        return "\n".join(lines)
