"""Synthetic and annotated dataset generator for training offline structure models.

Generates realistic labeled manuscript structures (academic papers, novels,
technical specifications, trade books) to train Logistic Regression and Decision Tree models.
"""

from pathlib import Path
import random
from typing import List, Tuple
import numpy as np

from app.core.ml.features import FEATURE_NAMES, FeatureExtractor
from app.models.ast import (
    ElementType,
    FigureElement,
    ListInfo,
    ParagraphElement,
    RunMetadata,
    TableCell,
    TableElement,
)


class ManuscriptDatasetGenerator:
    """Generates synthetic manuscripts with ground-truth structural labels."""

    SAMPLE_TITLES = [
        "The Architecture of Distributed Consensus Systems",
        "Principles of Quantum Computational Mechanics",
        "A Modern Theory of Algorithmic Complexity",
        "Deep Neural Representations in Computer Vision",
        "Statistical Foundations of Machine Learning",
        "The History of Information and Cybernetics",
        "Autonomous Multi-Agent Systems in Practice",
        "The Cryptographic Protocol Handbook",
        "Foundations of Software Verification",
        "Microservices at Global Scale",
    ]

    SAMPLE_AUTHORS = [
        "Dr. Eleanor Vance, Ph.D. — Department of Computer Science",
        "Alan Turing & Ada Lovelace — Institute for Advanced Study",
        "Prof. Marcus Brody, Department of Archaeology, Marshall College",
        "Dr. Sarah Connor, Cyberdyne Research Labs, email: sconnor@cyberdyne.org",
        "Prof. Richard Feynman, California Institute of Technology",
        "Dr. Grace Hopper & Claude Shannon, Naval Computing Laboratory",
    ]

    SAMPLE_CHAPTERS = [
        "Chapter 1: The Foundations of Computing",
        "Chapter 2: Concurrency and Parallel Execution",
        "Chapter 3: Fault Tolerance and Replication",
        "Chapter 4: Scalable Network Architectures",
        "Chapter 5: Cryptographic Invariants",
        "Chapter 6: Empirical Evaluation and Benchmarks",
        "Part I: Theoretical Underpinnings",
        "Part II: Systems Implementation",
        "Introduction and Problem Formulation",
        "Conclusion and Future Directions",
    ]

    SAMPLE_HEADINGS = [
        "1.1 The Theoretical Model",
        "1.2 System Architecture Overview",
        "2.1 Consensus Protocol Specification",
        "2.2 Leader Election Mechanics",
        "3.1 Log Replication and Durability",
        "3.2 Heartbeat Intervals and Timeout Bounds",
        "4.1 Micro-benchmark Methodology",
        "4.2 Throughput Analysis under Heavy Load",
        "Related Work and Literature Review",
        "Security Considerations and Threat Model",
    ]

    SAMPLE_SUBHEADINGS = [
        "1.1.1 Network Partition Scenarios",
        "1.1.2 Quorum Calculation Rules",
        "2.1.1 Monotonic Epoch Timestamps",
        "2.1.2 Rejection of Stale RPC Requests",
        "3.1.1 Write-Ahead Logging Invariants",
        "3.1.2 Asynchronous Disk Sync Strategies",
        "4.1.1 Hardware Specifications",
        "4.1.2 Synthetic Workload Parameters",
    ]

    SAMPLE_BODY_PARAGRAPHS = [
        "Distributed consensus represents one of the most critical challenges in modern software engineering. "
        "When autonomous nodes communicate across an unreliable asynchronous network, achieving agreement on shared state "
        "requires strict adherence to algorithmic protocols. Message delivery may be arbitrarily delayed, reordered, or duplicated.",
        
        "In this section, we analyze the performance characteristics of the proposed replication engine. Under sustained peak load, "
        "the system processes requests with bounded tail latency while maintaining linearizable consistency across all replicas. "
        "Experimental evaluations demonstrate that throughput scales linearly with the addition of storage shards.",
        
        "To guarantee that state mutations remain deterministic, each transaction receives a monotonically increasing sequence identifier. "
        "Replicas reject any operation containing an out-of-order sequence number, prompting a log synchronization reconciliation pass. "
        "This invariant ensures that divergence between the primary node and backup mirrors is mathematically impossible.",
        
        "The interaction between client sessions and cluster coordinators relies on lease-based heartbeats. If a coordinator fails "
        "to renew its lease before expiry, the cluster initiates an emergency election cycle. During the brief election window, "
        "read operations continue to be served from read-only cache snapshots.",
        
        "Memory overhead remains a vital metric for embedded applications. Our slotted canonical representation minimizes per-node "
        "pointer allocations, maintaining the entire document representation within predictable bounds even for manuscripts exceeding "
        "several hundred pages.",
    ]

    SAMPLE_LIST_ITEMS = [
        "High availability with zero single points of failure.",
        "Deterministic log replication with bounded tail latency.",
        "Cryptographic audit trails for all recorded state mutations.",
        "Automatic partition detection and cluster self-healing.",
        "Dynamic membership reconfiguration without service interruption.",
        "Sub-millisecond read latency on cached index tables.",
    ]

    SAMPLE_CAPTIONS = [
        "Figure 1.1: Distributed consensus state transition between Node A and Node B.",
        "Figure 2.3: Throughput scaling under varying network latency conditions.",
        "Table 3.1: Latency benchmarks across different cluster topologies.",
        "Figure 4.2: Fault tolerance recovery time following primary coordinator failure.",
        "Table 5.1: Comparative resource consumption between baseline and DocXpress.",
    ]

    SAMPLE_REFERENCES = [
        "1. Shannon, C. E. (1948). A Mathematical Theory of Communication. Bell System Technical Journal, 27(3), 379-423.",
        "2. Lamport, L. (1978). Time, clocks, and the ordering of events in a distributed system. Communications of the ACM, 21(7), 558-565.",
        "3. Turing, A. M. (1936). On computable numbers, with an application to the Entscheidungsproblem. Proceedings of the LMS, 42(1), 230-265.",
        "4. Ongaro, D., & Ousterhout, J. (2014). In search of an understandable consensus algorithm. USENIX ATC, 305-319.",
        "5. Dean, J., & Ghemawat, S. (2004). MapReduce: Simplified data processing on large clusters. OSDI, 137-150.",
        "6. Gray, J., & Reuter, A. (1992). Transaction Processing: Concepts and Techniques. Morgan Kaufmann Publishers.",
    ]

    @classmethod
    def generate_synthetic_corpus(
        cls,
        num_documents: int = 50,
        random_seed: int = 42,
    ) -> Tuple[np.ndarray, List[str]]:
        """Generates a synthetic training corpus of feature vectors and ground-truth labels.
        
        Args:
            num_documents: Number of simulated multi-section documents to generate.
            random_seed: Random seed for deterministic reproducibility.
            
        Returns:
            Tuple of (X: np.ndarray shape (N, 32), y: List[str]).
        """
        rng = random.Random(random_seed)
        all_features: List[List[float]] = []
        all_labels: List[str] = []

        for doc_idx in range(num_documents):
            doc_elements: List[Tuple[BaseElement, ElementType]] = []
            elem_idx = 0

            # 1. Title (Always present in front matter)
            title_text = rng.choice(cls.SAMPLE_TITLES)
            title_elem = ParagraphElement(
                element_id=f"syn_{doc_idx}_{elem_idx}",
                element_type=ElementType.TITLE,
                paragraph_index=elem_idx,
                original_text=title_text,
                original_style="Title",
                runs=(RunMetadata(text=title_text, bold=True, font_size_pt=24.0),),
            )
            doc_elements.append((title_elem, ElementType.TITLE))
            elem_idx += 1

            # 2. Author Details (Front matter)
            author_text = rng.choice(cls.SAMPLE_AUTHORS)
            author_elem = ParagraphElement(
                element_id=f"syn_{doc_idx}_{elem_idx}",
                element_type=ElementType.AUTHOR,
                paragraph_index=elem_idx,
                original_text=author_text,
                original_style="Subtitle",
                runs=(RunMetadata(text=author_text, italic=True, font_size_pt=12.0),),
            )
            doc_elements.append((author_elem, ElementType.AUTHOR))
            elem_idx += 1

            # 3. Multiple Chapters
            num_chapters = rng.randint(3, 7)
            for chap_num in range(num_chapters):
                # Chapter Heading
                chap_text = f"Chapter {chap_num + 1}: {rng.choice(cls.SAMPLE_CHAPTERS).split(': ')[-1]}"
                chap_elem = ParagraphElement(
                    element_id=f"syn_{doc_idx}_{elem_idx}",
                    element_type=ElementType.CHAPTER,
                    paragraph_index=elem_idx,
                    original_text=chap_text,
                    original_style="Heading 1",
                    runs=(RunMetadata(text=chap_text, bold=True, font_size_pt=18.0),),
                )
                doc_elements.append((chap_elem, ElementType.CHAPTER))
                elem_idx += 1

                # Body paragraphs under chapter
                for _ in range(rng.randint(2, 4)):
                    b_text = rng.choice(cls.SAMPLE_BODY_PARAGRAPHS)
                    b_elem = ParagraphElement(
                        element_id=f"syn_{doc_idx}_{elem_idx}",
                        element_type=ElementType.PARAGRAPH,
                        paragraph_index=elem_idx,
                        original_text=b_text,
                        original_style="Normal",
                        runs=(RunMetadata(text=b_text, font_size_pt=11.0),),
                    )
                    doc_elements.append((b_elem, ElementType.PARAGRAPH))
                    elem_idx += 1

                # Section Heading (H1)
                h_text = f"{chap_num + 1}.1 {rng.choice(cls.SAMPLE_HEADINGS).split(' ', 1)[-1]}"
                h_elem = ParagraphElement(
                    element_id=f"syn_{doc_idx}_{elem_idx}",
                    element_type=ElementType.HEADING,
                    paragraph_index=elem_idx,
                    original_text=h_text,
                    original_style="Heading 2",
                    runs=(RunMetadata(text=h_text, bold=True, font_size_pt=14.0),),
                )
                doc_elements.append((h_elem, ElementType.HEADING))
                elem_idx += 1

                # Body paragraph
                b_text = rng.choice(cls.SAMPLE_BODY_PARAGRAPHS)
                b_elem = ParagraphElement(
                    element_id=f"syn_{doc_idx}_{elem_idx}",
                    element_type=ElementType.PARAGRAPH,
                    paragraph_index=elem_idx,
                    original_text=b_text,
                    original_style="Normal",
                    runs=(RunMetadata(text=b_text, font_size_pt=11.0),),
                )
                doc_elements.append((b_elem, ElementType.PARAGRAPH))
                elem_idx += 1

                # Subheading (H2)
                sh_text = f"{chap_num + 1}.1.1 {rng.choice(cls.SAMPLE_SUBHEADINGS).split(' ', 1)[-1]}"
                sh_elem = ParagraphElement(
                    element_id=f"syn_{doc_idx}_{elem_idx}",
                    element_type=ElementType.SUBHEADING,
                    paragraph_index=elem_idx,
                    original_text=sh_text,
                    original_style="Heading 3",
                    runs=(RunMetadata(text=sh_text, bold=True, italic=True, font_size_pt=12.0),),
                )
                doc_elements.append((sh_elem, ElementType.SUBHEADING))
                elem_idx += 1

                # Body paragraph
                b_text = rng.choice(cls.SAMPLE_BODY_PARAGRAPHS)
                b_elem = ParagraphElement(
                    element_id=f"syn_{doc_idx}_{elem_idx}",
                    element_type=ElementType.PARAGRAPH,
                    paragraph_index=elem_idx,
                    original_text=b_text,
                    original_style="Normal",
                    runs=(RunMetadata(text=b_text, font_size_pt=11.0),),
                )
                doc_elements.append((b_elem, ElementType.PARAGRAPH))
                elem_idx += 1

                # Occasional Table
                if rng.random() > 0.4:
                    tbl_elem = TableElement(
                        element_id=f"syn_{doc_idx}_{elem_idx}",
                        element_type=ElementType.TABLE,
                        paragraph_index=elem_idx,
                        original_text="Node ID\tThroughput\tStatus\nnode-01\t12000\tActive",
                        rows_count=2,
                        cols_count=3,
                        cells=(),
                    )
                    doc_elements.append((tbl_elem, ElementType.TABLE))
                    elem_idx += 1

                    # Caption for Table
                    cap_text = f"Table {chap_num + 1}.1: Performance benchmarks for Chapter {chap_num + 1}."
                    cap_elem = ParagraphElement(
                        element_id=f"syn_{doc_idx}_{elem_idx}",
                        element_type=ElementType.CAPTION,
                        paragraph_index=elem_idx,
                        original_text=cap_text,
                        original_style="Caption",
                        runs=(RunMetadata(text=cap_text, italic=True, font_size_pt=9.5),),
                    )
                    doc_elements.append((cap_elem, ElementType.CAPTION))
                    elem_idx += 1

                # Occasional Figure
                if rng.random() > 0.4:
                    fig_elem = FigureElement(
                        element_id=f"syn_{doc_idx}_{elem_idx}",
                        element_type=ElementType.FIGURE,
                        paragraph_index=elem_idx,
                        original_text="",
                        image_id="rId10",
                        width_pt=280.0,
                        height_pt=140.0,
                    )
                    doc_elements.append((fig_elem, ElementType.FIGURE))
                    elem_idx += 1

                    # Caption for Figure
                    cap_text = f"Figure {chap_num + 1}.1: Architectural schematic for Chapter {chap_num + 1}."
                    cap_elem = ParagraphElement(
                        element_id=f"syn_{doc_idx}_{elem_idx}",
                        element_type=ElementType.CAPTION,
                        paragraph_index=elem_idx,
                        original_text=cap_text,
                        original_style="Caption",
                        runs=(RunMetadata(text=cap_text, italic=True, font_size_pt=9.5),),
                    )
                    doc_elements.append((cap_elem, ElementType.CAPTION))
                    elem_idx += 1

                # Occasional List Items
                if rng.random() > 0.3:
                    for l_idx in range(rng.randint(2, 4)):
                        is_ordered = (rng.random() > 0.5)
                        item_text = rng.choice(cls.SAMPLE_LIST_ITEMS)
                        if is_ordered:
                            prefix = f"{l_idx + 1}. "
                        else:
                            prefix = "* "
                        full_item_text = prefix + item_text
                        list_elem = ParagraphElement(
                            element_id=f"syn_{doc_idx}_{elem_idx}",
                            element_type=ElementType.LIST,
                            paragraph_index=elem_idx,
                            original_text=full_item_text,
                            original_style="List Bullet" if not is_ordered else "List Number",
                            list_info=ListInfo(is_bullet=not is_ordered, is_numbered=is_ordered),
                            runs=(RunMetadata(text=full_item_text, font_size_pt=11.0),),
                        )
                        doc_elements.append((list_elem, ElementType.LIST))
                        elem_idx += 1

            # 4. Back-Matter References Section
            ref_header = ParagraphElement(
                element_id=f"syn_{doc_idx}_{elem_idx}",
                element_type=ElementType.HEADING,
                paragraph_index=elem_idx,
                original_text="References",
                original_style="Heading 1",
                runs=(RunMetadata(text="References", bold=True, font_size_pt=16.0),),
            )
            doc_elements.append((ref_header, ElementType.HEADING))
            elem_idx += 1

            # Reference entries
            for r_idx in range(rng.randint(3, 6)):
                ref_text = rng.choice(cls.SAMPLE_REFERENCES)
                ref_elem = ParagraphElement(
                    element_id=f"syn_{doc_idx}_{elem_idx}",
                    element_type=ElementType.REFERENCE,
                    paragraph_index=elem_idx,
                    original_text=ref_text,
                    original_style="Normal",
                    runs=(RunMetadata(text=ref_text, font_size_pt=9.5),),
                )
                doc_elements.append((ref_elem, ElementType.REFERENCE))
                elem_idx += 1

            # Extract features for all elements in this synthetic document
            total_elems = len(doc_elements)
            for i, (elem, label) in enumerate(doc_elements):
                prev_e = doc_elements[i - 1][0] if i > 0 else None
                next_e = doc_elements[i + 1][0] if i < total_elems - 1 else None
                feat_dict = FeatureExtractor.extract_element_features(
                    elem=elem,
                    index=i,
                    total_elements=total_elems,
                    prev_elem=prev_e,
                    next_elem=next_e,
                    median_font_size=11.0,
                )
                all_features.append([feat_dict[name] for name in FEATURE_NAMES])
                all_labels.append(label.value)

        return np.array(all_features, dtype=np.float32), all_labels
