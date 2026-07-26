import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from workflow_contracts import (  # noqa: E402
    ArtifactEdge,
    ArtifactNode,
    ArtifactPassport,
    CapabilityIndex,
    CapabilityRecord,
    DeepReadCardRecord,
    DownloadManifestItem,
    FigureEvidenceRecord,
    FigureIndexRecord,
    EvidenceSourceRecord,
    PaperCard,
    RetrievalCandidate,
    RetrievalIndexManifest,
    SearchResultRecord,
    as_chinese_papers,
    capability_index_payload,
    deep_read_cards_payload,
    dois_from_download_items,
    evidence_pack_payload,
    figure_evidence_payload,
    figure_index_payload,
    inspect_mineru_zip,
    load_search_records,
    normalize_doi,
    retrieval_candidates_payload,
    retrieval_manifest_payload,
    stable_source_id,
    validate_artifact_passport,
    write_workflow_json,
)


class WorkflowContractsTest(unittest.TestCase):
    def test_normalize_doi_variants(self):
        self.assertEqual(
            normalize_doi("https://doi.org/10.1016/j.test.2024.01.001."),
            "10.1016/j.test.2024.01.001",
        )
        self.assertEqual(normalize_doi("doi:10.1109/TEST.2024.123"), "10.1109/TEST.2024.123")

    def test_artifact_graph_schema_accepts_direct_entry_unlinked_edges(self):
        passport = ArtifactPassport(
            nodes=[
                ArtifactNode(
                    node_id="node-pdf",
                    node_type="pdf_attachment",
                    trace_status="unlinked",
                    risk_flags=["unlinked_pdf"],
                ),
                ArtifactNode(
                    node_id="node-evidence",
                    node_type="evidence_item",
                    trace_status="inferred",
                ),
            ],
            edges=[
                ArtifactEdge(
                    edge_id="edge-1",
                    source_node_id="node-pdf",
                    target_node_id="node-evidence",
                    relation="derived_from",
                    confidence="inferred",
                )
            ],
        )

        self.assertEqual(validate_artifact_passport(passport), [])

    def test_artifact_graph_schema_rejects_invalid_confidence(self):
        passport = ArtifactPassport(
            nodes=[ArtifactNode(node_id="node-1", node_type="pdf_attachment", trace_status="certain")],
        )

        errors = validate_artifact_passport(passport)

        self.assertTrue(any("trace_status is invalid" in error for error in errors))

    def test_chinese_article_url_only_routes_to_manifest(self):
        record = SearchResultRecord.from_search_result({
            "title": "薄壁管弯曲回弹研究",
            "source": "wanfang",
            "article_url": "https://www.wanfangdata.com.cn/details/detail.do?_type=perio&id=test",
            "verification_status": "VERIFIED",
        })

        self.assertTrue(record.source_id.startswith("wanfang."))
        self.assertEqual(record.download_hint, "chinese_article_url")

        item = DownloadManifestItem.from_search_record(record)
        self.assertEqual(item.status, "ready")
        self.assertTrue(item.article_url.startswith("https://www.wanfangdata.com.cn/"))

    def test_warn_reject_fields_preserved(self):
        record = SearchResultRecord.from_search_result({
            "title": "Questionable paper",
            "source": "crossref",
            "doi": "10.1234/example",
            "verification_status": "WARN",
            "verification_confidence": "low",
            "warn_class": "metadata_mismatch",
        })

        self.assertEqual(record.verification_status, "WARN")
        self.assertEqual(record.verification_confidence, "low")
        self.assertEqual(record.warn_class, "metadata_mismatch")

    def test_oa_hint_fields_roundtrip_to_download_manifest(self):
        record = SearchResultRecord.from_search_result({
            "title": "OA paper",
            "source": "openalex",
            "doi": "10.5555/oa.demo",
            "oa_status": "candidate",
            "oa_source": "openalex",
            "oa_pdf_url": "https://example.org/paper.pdf",
            "oa_landing_url": "https://example.org/paper",
            "oa_license": "cc-by",
            "oa_checked_at": "2026-06-22T10:00:00",
        })
        item = DownloadManifestItem.from_search_record(record)

        self.assertEqual(record.oa_status, "candidate")
        self.assertEqual(item.oa_pdf_url, "https://example.org/paper.pdf")
        self.assertEqual(item.oa_source, "openalex")
        self.assertEqual(item.oa_license, "cc-by")

    def test_paper_card_normalization_and_outputs(self):
        card = PaperCard.from_value({
            "evidence_role": "method",
            "primary_claim": "提出一种新方法",
            "main_methods_or_baselines": ["POD", "POD-Galerkin"],
            "reading_depth": "abstract-only",
            "content_fit": "adjacent",
            "content_fit_note": "方法相近但工况不同",
            "usable_for": ["方法参照"],
            "not_usable_for": ["强结论"],
        })

        self.assertEqual(card.evidence_role, "method")
        self.assertEqual(card.reading_depth, "abstract_only")
        self.assertEqual(card.content_fit, "adjacent")
        self.assertIn("mp-role:method", card.zotero_tags("T1"))
        self.assertIn("mp-fit:adjacent", card.zotero_tags("T1"))
        self.assertIn("mp-depth:abstract-only", card.zotero_tags("T1"))
        note = card.zotero_child_note(
            record_id="rec-1",
            citekey="demo2026",
            paper_tier="T1",
            trust_status="VERIFIED",
            search_task_id="S1",
            chapter_id="2.1",
            updated_at="2026-06-17",
        )
        self.assertIn("More-Paper Evidence Card", note)
        self.assertIn("evidence_role: method", note)
        self.assertIn("record_id: rec-1", note)
        self.assertIn("search_task_id: S1", note)

    def test_search_result_record_carries_paper_card(self):
        record = SearchResultRecord.from_search_result({
            "title": "Demo",
            "source": "openalex",
            "paper_card": {
                "evidence_role": "review",
                "primary_claim": "总结领域现状",
                "reading_depth": "metadata_only",
                "content_fit": "background_only",
            },
        })

        self.assertEqual(record.paper_card.evidence_role, "review")
        self.assertEqual(record.paper_card.reading_depth, "metadata_only")
        self.assertEqual(record.paper_card.content_fit, "background_only")

    def test_search_result_record_preserves_weighted_score_audit_fields(self):
        record = SearchResultRecord.from_search_result({
            "title": "Demo",
            "_weighted_score": 18.75,
            "_score_dimensions": {"topic_match": 4, "method_rigor": 3},
            "_score_weights": {"topic_match": 0.35, "method_rigor": 0.2},
            "_score_reasons": ["topic_match=4"],
            "_score_confidence": "medium",
            "_uncertainty_flags": ["venue_quality_unresolved"],
        })
        self.assertEqual(record.weighted_score, 18.75)
        self.assertEqual(record.score_dimensions["topic_match"], 4)
        self.assertEqual(record.score_confidence, "medium")
        self.assertIn("venue_quality_unresolved", record.uncertainty_flags)

    def test_search_result_record_preserves_discovery_provenance(self):
        record = SearchResultRecord.from_search_result({
            "title": "Demo", "source": "openalex",
            "discovered_sources": ["openalex", "crossref"],
            "metadata_sources": {"abstract": "openalex", "doi": "crossref"},
            "discovery_round": 2, "discovery_rounds": [1, 2], "discovery_strategy": "cited",
        })
        self.assertEqual(record.discovered_sources, ["openalex", "crossref"])
        self.assertEqual(record.metadata_sources["doi"], "crossref")
        self.assertEqual(record.discovery_round, 2)
        self.assertEqual(record.discovery_rounds, [1, 2])
        self.assertEqual(record.discovery_strategy, "cited")

    def test_workflow_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflow.json"
            records = [
                SearchResultRecord.from_search_result({
                    "title": "A DOI paper",
                    "source": "openalex",
                    "doi": "https://doi.org/10.5555/demo",
                    "year": "2024",
                    "paper_card": {
                        "evidence_role": "theory",
                        "primary_claim": "提出一个概念框架",
                        "reading_depth": "full_text",
                        "content_fit": "direct",
                    },
                }),
                SearchResultRecord.from_search_result({
                    "title": "A CNKI paper",
                    "source": "cnki",
                    "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=demo",
                }),
            ]

            write_workflow_json(path, records, {"query": "demo"})
            data = json.loads(path.read_text(encoding="utf-8"))
            loaded = load_search_records(path)

        self.assertEqual(data["schema_version"], "workflow-contracts.v1")
        self.assertEqual(data["artifact_type"], "search_results")
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].doi, "10.5555/demo")
        self.assertEqual(loaded[0].paper_card.evidence_role, "theory")
        self.assertTrue(loaded[1].source_id.startswith("cnki."))

    def test_download_item_views(self):
        items = [
            DownloadManifestItem(title="English", doi="10.5555/demo", source="openalex"),
            DownloadManifestItem(
                title="中文",
                source="cnki",
                source_id=stable_source_id("cnki", "中文"),
                article_url="https://kns.cnki.net/kcms/detail/detail.aspx?filename=demo",
            ),
        ]

        self.assertEqual(dois_from_download_items(items), ["10.5555/demo"])
        chinese = as_chinese_papers(items)
        self.assertEqual(len(chinese), 1)
        self.assertEqual(chinese[0]["source"], "cnki")

    def test_retrieval_manifest_payload(self):
        manifest = RetrievalIndexManifest(
            generated_at="2026-06-14T10:00:00+08:00",
            index_scope="search_results",
            source_artifacts=["workflow_search_results.json"],
            search_task_ids=["S1", "S2"],
            source_count=3,
            record_count=120,
            index_levels=["lightweight", "pdf_chunk"],
            sources=["zotero_notes", "pdf_chunks"],
            item_count=12,
            chunk_count=34,
            reusable_for=["step5_download_routing", "step7_candidate_locator"],
            authority="candidate_only",
            staleness="fresh",
            rebuild_triggers=["search_tasks_changed"],
            warnings=["candidate only"],
            notes="candidate retrieval only",
        )
        payload = retrieval_manifest_payload(manifest)
        self.assertEqual(payload["schema_version"], "retrieval-index.v1")
        self.assertEqual(payload["index_scope"], "search_results")
        self.assertEqual(payload["source_artifacts"], ["workflow_search_results.json"])
        self.assertEqual(payload["search_task_ids"], ["S1", "S2"])
        self.assertEqual(payload["source_count"], 3)
        self.assertEqual(payload["record_count"], 120)
        self.assertEqual(payload["item_count"], 12)
        self.assertEqual(payload["index_levels"], ["lightweight", "pdf_chunk"])
        self.assertEqual(payload["reusable_for"], ["step5_download_routing", "step7_candidate_locator"])
        self.assertEqual(payload["authority"], "candidate_only")
        self.assertEqual(payload["staleness"], "fresh")
        self.assertEqual(payload["rebuild_triggers"], ["search_tasks_changed"])

    def test_capability_index_payload(self):
        index = CapabilityIndex(
            generated_at="2026-06-14T10:00:00+08:00",
            project_root="/tmp/project",
            asset_summary={"bibtex": 20, "pdf": 18, "zotero_items": 20},
            capabilities=[
                CapabilityRecord(
                    capability_id="zotero_mapping_ready",
                    source_artifact="文献-Zotero架构对照.json",
                    status="available",
                    supports_steps=["Step 6", "Step 7"],
                    supports_actions=["writing", "citation_audit"],
                    evidence_boundary="metadata_and_attachment_index",
                    risk_note="PDF evidence still requires direct verification",
                )
            ],
            recommended_entry_points=["Step 7"],
            blocking_gaps=[],
            warnings=["candidate evidence is not proof"],
            next_action="enter Step 7 with evidence confirmation",
        )
        payload = capability_index_payload(index)
        self.assertEqual(payload["schema_version"], "capability-index.v1")
        self.assertEqual(payload["asset_summary"]["pdf"], 18)
        self.assertEqual(payload["capabilities"][0]["capability_id"], "zotero_mapping_ready")
        self.assertEqual(payload["capabilities"][0]["status"], "available")
        self.assertIn("Step 7", payload["capabilities"][0]["supports_steps"])
        self.assertEqual(payload["capabilities"][0]["evidence_boundary"], "metadata_and_attachment_index")
        self.assertEqual(payload["recommended_entry_points"], ["Step 7"])

    def test_retrieval_candidates_payload(self):
        candidates = [
            RetrievalCandidate(
                chapter_id="2.3",
                chapter_title="HFO 工质替代的研究现状",
                claim_id="claim-1",
                claim_text="HFO 替代路径需要同时比较热物性与环境指标",
                evidence_question_id="eq-1",
                query_text="claim about heat transfer",
                query_variant="heat property + environmental indicator",
                step_context="7.7",
                candidate_item_key="ABC123",
                candidate_chunk_id="chunk-1",
                page="12",
                source_page_hint="p.12 methods paragraph",
                source_type="pdf_chunk",
                retrieval_score="0.92",
                match_reason="keyword overlap",
                negative_or_conflicting_evidence="candidate suggests only partial environmental comparison",
                requires_direct_verification=True,
                post_verify_status="",
            )
        ]
        payload = retrieval_candidates_payload(candidates, {"chapter": "ch3"})
        self.assertEqual(payload["schema_version"], "retrieval-candidates.v1")
        self.assertEqual(payload["metadata"]["chapter"], "ch3")
        self.assertEqual(payload["candidates"][0]["chapter_id"], "2.3")
        self.assertEqual(payload["candidates"][0]["claim_id"], "claim-1")
        self.assertEqual(payload["candidates"][0]["claim_text"], "HFO 替代路径需要同时比较热物性与环境指标")
        self.assertEqual(payload["candidates"][0]["evidence_question_id"], "eq-1")
        self.assertEqual(payload["candidates"][0]["query_variant"], "heat property + environmental indicator")
        self.assertEqual(payload["candidates"][0]["candidate_item_key"], "ABC123")
        self.assertEqual(payload["candidates"][0]["source_page_hint"], "p.12 methods paragraph")
        self.assertIn("partial environmental comparison", payload["candidates"][0]["negative_or_conflicting_evidence"])
        self.assertTrue(payload["candidates"][0]["requires_direct_verification"])

    def test_figure_index_payload(self):
        records = [
            FigureIndexRecord(
                item_key="ABC123",
                figure_id="fig_3",
                figure_type="figure",
                page="12",
                caption="Temperature distribution under condition A",
                mentions_in_text=["As shown in Fig. 3"],
                source_type="caption_plus_text",
                collection_path=["ch3", "results"],
                paper_tier="T1",
            )
        ]
        payload = figure_index_payload(records, {"chapter": "ch3"})
        self.assertEqual(payload["schema_version"], "figure-index.v1")
        self.assertEqual(payload["records"][0]["figure_id"], "fig_3")
        self.assertEqual(payload["records"][0]["source_type"], "caption_plus_text")

    def test_evidence_pack_payload(self):
        records = [
            EvidenceSourceRecord(
                source_path="reports/experiment.md",
                source_type="report",
                evidence_level="author_provided",
                claim_scope="strong_claim_if_traceable",
                risk_flags=["author_confirmation_needed"],
                verification_action="confirm_author_or_source_context",
            )
        ]
        payload = evidence_pack_payload(records, {"entry_mode": "evidence_pack"})
        self.assertEqual(payload["schema_version"], "evidence-pack.v1")
        self.assertEqual(payload["metadata"]["entry_mode"], "evidence_pack")
        self.assertEqual(payload["records"][0]["source_type"], "report")
        self.assertEqual(payload["records"][0]["evidence_level"], "author_provided")

    def test_deep_read_cards_payload(self):
        records = [
            DeepReadCardRecord(
                record_id="stable-001",
                citekey="wang2024example",
                title="Example Paper",
                section_id="2.1",
                section_title="热管理方法",
                reading_depth="abstract_only",
                evidence_role="method",
                content_fit="direct",
                claim_summary="提出一个示例方法。",
                method_summary="使用模拟辅助控制框架。",
                experiment_summary="待补全文确认实验设置与结果。",
                mechanism_hints={
                    "phenomenon": "温升变化",
                    "state_variables": ["current", "temperature"],
                    "causal_chain": ["电流增加导致热损耗上升。"],
                    "claim_limit": "候选解释，需补全文确认。",
                },
                usable_for=["方法综述"],
                not_usable_for=["强结论"],
                source_trace={"text_source": "abstract_only"},
            )
        ]
        payload = deep_read_cards_payload(records, {"entry_mode": "deep_read_refine"})
        self.assertEqual(payload["schema_version"], "deep-read-cards.v1")
        self.assertEqual(payload["metadata"]["entry_mode"], "deep_read_refine")
        self.assertEqual(payload["records"][0]["reading_depth"], "abstract_only")
        self.assertIn("causal_chain", payload["records"][0]["mechanism_hints"])
        self.assertEqual(payload["records"][0]["source_trace"]["text_source"], "abstract_only")

    def test_inspect_mineru_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "LLM-for-Zotero-MinerU-cache-ABC123.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("_llm_source.json", json.dumps({
                    "parentItemKey": "ITEM123",
                    "attachmentKey": "ABC123",
                    "sourceFilename": "paper.pdf",
                }))
                zf.writestr("full.md", "# Demo\n\n![](images/fig.jpg)\n")
                zf.writestr("manifest.json", json.dumps({"sections": []}))
                zf.writestr("content_list.json", "[]")
                zf.writestr("images/fig.jpg", b"fake")

            summary = inspect_mineru_zip(zip_path)

        self.assertEqual(summary.parent_item_key, "ITEM123")
        self.assertEqual(summary.attachment_key, "ABC123")
        self.assertTrue(summary.has_full_md)
        self.assertTrue(summary.has_manifest_json)
        self.assertEqual(summary.image_count, 1)
        self.assertEqual(summary.warnings, [])

    def test_inspect_missing_mineru_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "missing.zip"

            summary = inspect_mineru_zip(zip_path)

        self.assertEqual(summary.warnings, ["zip_missing"])
        self.assertEqual(summary.zip_path, zip_path.as_posix())

    def test_figure_evidence_payload(self):
        records = [
            FigureEvidenceRecord(
                figure_id="fig_3",
                item_key="ABC123",
                claim_binding="claim-7",
                figure_intent="Compare temperature distribution under condition A",
                evidence_basis="data/results.csv + PDF p.12 figure caption",
                candidate_specs=[{"chart_type": "heatmap", "data_source": "results.csv"}],
                human_selected_candidate="heatmap",
                figure_risk_note="visual confirmation pending",
                caption_support="partial",
                text_support="strong",
                visual_support="pending",
                evidence_status="text_caption_aligned",
                recommended_action="retain",
                generation_backend="reproduction",
                visualspec_path="visualspec.json",
                reproduction_bundle="figures/fig_3_bundle",
                manifest_path="figures/fig_3_bundle/reproduction_manifest.json",
                reproduction_status="semantic_near_pass",
                qa_profile="semantic",
                verification_status="pass",
                figure_asset_action="digitize",
                figure_transform_authorization="explicit_user_request",
                extraction_project_path="figures/fig_3/figure_project.result.json",
                extraction_report_path="figures/fig_3/extraction_report.json",
                extraction_status="formal_data_ready",
                review_status="complete",
                review_decisions_path="figures/fig_3/review-decisions.json",
                observations_path="figures/fig_3/observations.csv",
                data_path="figures/fig_3/data.csv",
                data_sha256="a" * 64,
                visualspec_data_sha256="a" * 64,
                value_delivery_authorized=True,
            )
        ]
        payload = figure_evidence_payload(records, {"step": "7.11"})
        self.assertEqual(payload["schema_version"], "figure-evidence.v1")
        self.assertEqual(payload["records"][0]["figure_intent"], "Compare temperature distribution under condition A")
        self.assertEqual(payload["records"][0]["candidate_specs"][0]["chart_type"], "heatmap")
        self.assertEqual(payload["records"][0]["human_selected_candidate"], "heatmap")
        self.assertEqual(payload["records"][0]["figure_risk_note"], "visual confirmation pending")
        self.assertEqual(payload["records"][0]["evidence_status"], "text_caption_aligned")
        self.assertEqual(payload["records"][0]["recommended_action"], "retain")
        self.assertEqual(payload["records"][0]["generation_backend"], "reproduction")
        self.assertEqual(payload["records"][0]["verification_status"], "pass")
        self.assertEqual(payload["records"][0]["figure_asset_action"], "digitize")
        self.assertEqual(
            payload["records"][0]["figure_transform_authorization"],
            "explicit_user_request",
        )
        self.assertEqual(payload["records"][0]["extraction_status"], "formal_data_ready")
        self.assertEqual(payload["records"][0]["review_status"], "complete")
        self.assertEqual(payload["records"][0]["data_sha256"], "a" * 64)
        self.assertTrue(payload["records"][0]["value_delivery_authorized"])


if __name__ == "__main__":
    unittest.main()
