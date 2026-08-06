from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read_rel(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class PublicDocsTest(unittest.TestCase):
    def test_readme_has_three_public_entry_prompts(self):
        readme = read_rel("README.md")
        for token in [
            "定题入口",
            "直达下载入口",
            "写作入口",
            "examples/first-run/README.md",
            "examples/demo/step8-ai-trace-demo/",
            "python3 scripts/run_step8_ai_trace.py --project-root examples/demo/step8-ai-trace-demo",
            "先发散、后收敛、候选池先保留",
            "输入边界、候选池、输出工件和失败回退",
            "先把主题、假设、路线和反例放进候选池，再把当前轮收敛成一个执行包",
        ]:
            self.assertIn(token, readme)

    def test_first_run_examples_exist(self):
        for rel in [
            "examples/first-run/README.md",
            "examples/first-run/step1-topic-sample.md",
            "examples/first-run/step5-download-summary.md",
            "examples/first-run/step7-writing-sample.md",
            "examples/demo/demo-script.md",
            "examples/demo/step8-ai-trace-demo/README.md",
            "examples/demo/step8-ai-trace-demo/论文初稿.md",
            "examples/showcase/diagnostic_summary_ai_trace_sample.md",
            "examples/showcase/revision_ledger_ai_trace_sample.json",
            "examples/showcase/step8_ai_trace_demo.md",
        ]:
            self.assertTrue((ROOT / rel).exists(), rel)

    def test_marketplace_manifest_exists(self):
        self.assertTrue((ROOT / ".claude-plugin/marketplace.json").exists())

    def test_skill_mentions_public_first_examples(self):
        skill = read_rel("SKILL.md")
        self.assertIn("Public-first entry examples", skill)
        self.assertIn("README 首屏", skill)

    def test_global_nature_skills_principles_are_public_without_new_numbered_entry(self):
        skill = read_rel("SKILL.md")
        readme = read_rel("README.md")
        routing = read_rel("references/entry-routing-index.md")

        for token in [
            "张力先行",
            "双向校准",
            "最小对比",
            "反模式命名",
            "任务定义优先于实现定义",
            "契约变更 vs 实现变更",
            "快速通道不跳质量门",
        ]:
            self.assertIn(token, skill)

        for token in [
            "现有 8 步",
            "快速通道不跳质量门",
            "任意 Step 直达",
            "docs/assets/marketing/more-paper-workflow-readme-hero-v1.0.26.png",
        ]:
            self.assertIn(token, readme)

        self.assertNotIn("运行契约兼容索引", readme)
        self.assertNotIn("## 宣传视觉与流程图", readme)

        self.assertIn("Public routing remains Step 1-8 only", routing)
        self.assertIn("Direct-entry is a fast path, not a quality bypass", routing)

        for text in [skill, readme, routing]:
            self.assertNotIn("Step 0:", text)
            self.assertNotIn("Step 0：", text)
            self.assertNotIn("- Step 0", text)

    def test_search_and_zotero_entry_docs_keep_boundary_separated(self):
        search = read_rel("commands/search.md")
        zotero = read_rel("commands/zotero.md")
        self.assertIn("关键词分层只服务检索式构造", search)
        self.assertIn("真正的 Zotero 分类与集合组织留到 Step 6", search)
        self.assertIn("Step 6 才是文献与大纲二级标题对齐的 Zotero 集合组织入口", zotero)
        self.assertIn("Zotero 根集合为论文标题", zotero)
        self.assertIn("一级集合只作为一级章节容器", zotero)
        self.assertIn("文献默认直接归入对应的大纲二级章节集合", zotero)
        self.assertIn("按小节集合限定证据链范围", zotero)
        self.assertIn("Step 3 的关键词分层只用于检索表达，不作为 Zotero 分类规则", zotero)

    def test_update_reminder_protocol_is_public_and_host_agnostic(self):
        protocol = read_rel("references/update-reminder-protocol.md")
        for token in [
            "更新提醒协议（宿主无关）",
            "显示文本 + 接收用户回复",
            "宿主若支持原生按钮/弹窗，优先使用原生选项交互",
            "若宿主不支持原生按钮/弹窗，则显示 `render_update_prompt.py` 生成的标准文本",
            "升级 / 本次跳过 / 今日不再提醒",
            "升级失败，但将继续使用当前本地版本",
            "python3 \"$SKILL_DIR/scripts/check_skill_update.py\" --json",
            "--record-choice snooze_today",
            "只有远程版本号高于本地版本号时才设置 `should_prompt=true`",
            "工作区无未提交修改",
        ]:
            self.assertIn(token, protocol)
        skill = read_rel("SKILL.md")
        self.assertIn("在选择 Step 路由前先执行", skill)
        self.assertIn("should_prompt=true", skill)

    def test_step8_ai_trace_runtime_state_source_is_publicly_documented(self):
        readme = read_rel("README.md")
        showcase = read_rel("examples/showcase/README.md")
        step8_entry = read_rel("agents/step_8_entry.md")

        for text in [readme, showcase, step8_entry]:
            self.assertIn(".skill-state/ai_trace_diagnostics.json", text)

        self.assertIn("runtime 状态源", readme)
        self.assertIn("artifact_passport.json", readme)
        self.assertIn("运行态状态源之一", showcase)
        self.assertIn("status_contract", step8_entry)

    def test_step8_ai_trace_demo_is_a_minimal_hands_on_recipe(self):
        demo = read_rel("examples/showcase/step8_ai_trace_demo.md")
        for token in [
            "## 最小目录结构",
            "demo-project/",
            "## 命令 1：进入项目目录",
            "## 命令 2：运行 Step 8 AI Trace 入口",
            "## 命令 3：检查产物",
            ".skill-state/ai_trace_diagnostics.json",
            "diagnostic_summary.md",
            "revision_ledger.json",
            "revision_ledger.md",
            "润色质量报告.md",
            "### Step 8 总判断",
            "### 统一状态契约",
        ]:
            self.assertIn(token, demo)

    def test_step8_ai_trace_demo_folder_is_copyable(self):
        demo = read_rel("examples/demo/step8-ai-trace-demo/README.md")
        draft = read_rel("examples/demo/step8-ai-trace-demo/论文初稿.md")
        self.assertIn("python3 scripts/run_step8_ai_trace.py --project-root examples/demo/step8-ai-trace-demo", demo)
        self.assertIn("论文初稿.md", demo)
        self.assertIn("值得注意的是", draft)
        self.assertIn("这里需要补文献", draft)

    def test_step4_dashboard_is_default_and_discoverable(self):
        readme = read_rel("README.md")
        step4 = read_rel("agents/step_4_search_score.md")
        triggers = read_rel("references/trigger-catalog.md")

        self.assertIn("step4-dashboard/", readme)
        self.assertIn("标准 Step 4 完成链路必须默认生成本地可视化看板", step4)
        self.assertIn("Step 4 可视化看板已生成", step4)
        self.assertIn("step4-dashboard/index.html", step4)
        for token in [
            "检索结果看板",
            "检索结果可视化",
            "下载优先级看板",
            "search results dashboard",
        ]:
            self.assertIn(token, triggers)


if __name__ == "__main__":
    unittest.main()
