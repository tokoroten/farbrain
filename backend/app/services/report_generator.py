"""Report generation service with LLM analysis."""

import logging
from typing import Dict, List, Any

from backend.app.services.llm import get_llm_service

logger = logging.getLogger(__name__)


# Prompts for LLM analysis
CLUSTER_ANALYSIS_PROMPT = """あなたはブレインストーミングの分析専門家です。
以下のクラスタに含まれるアイディアを分析し、洞察を提供してください。

【クラスタ情報】
クラスタ名: {cluster_label}
アイディア数: {idea_count}

【セッションコンテキスト】
テーマ: {session_theme}
参加者数: {participant_count}

【アイディアのサンプル（ランダム抽出）】
{ideas_list}

以下の観点で分析してください:

1. このテーマの特徴（200-300字）
   - どのような観点のアイディアが集まったか
   - このテーマの独自性や重要性
   - 参加者の思考の傾向

2. 深掘り分析（300-400字）
   - このテーマ内での多様性
   - 特に注目すべきアイディアとその理由（最低3つ言及）
   - 実現可能性の評価
   - 他のテーマとの関連性の可能性

3. 次のステップ（150-200字）
   - このテーマをさらに発展させる具体的な提案
   - 優先すべきアクション

各セクションは見出しを付けて、読みやすく構成してください。
"""


OVERALL_CONCLUSION_PROMPT = """あなたはブレインストーミングの総括を行う専門家です。
以下のセッションデータを総合的に分析し、総括を作成してください。

【セッション情報】
テーマ: {session_theme}
参加者数: {participant_count}
総アイディア数: {total_ideas}
テーマ（クラスタ）数: {cluster_count}

【各クラスタの洞察】
{cluster_insights_summary}

以下の観点で総括を作成してください:

1. 全体総括（500-800字）
   - セッション全体で得られた知見の統合
   - 複数のテーマに共通する思考パターン
   - 予想外の発見や興味深い組み合わせ
   - 参加者全体の創造性の方向性と特徴

2. イノベーションの方向性（300-400字）
   - 最も有望なアイディアの組み合わせ
   - クラスタ間の融合によって生まれる新しい可能性
   - 実現に向けた優先順位の提案

3. テーマ間の関係性（200-300字）
   - 具体的にどのクラスタとどのクラスタが補完関係にあるか
   - 対立する観点がある場合、そのバランスの取り方
   - 統合すべきテーマの提案

4. 注意すべきギャップ（150-200字）
   - 議論が薄かった領域
   - 今後検討すべき観点

5. メタ分析（200-300字）
   - 参加者の思考プロセスの特徴
   - グループダイナミクスの観察
   - セッションの質と今後の改善点

各セクションは見出しを付けて、読みやすく構成してください。
"""


class ReportGenerator:
    """Generate reports with LLM analysis."""

    def __init__(self):
        """Initialize report generator."""
        self.llm_service = None

    async def _ensure_llm_service(self):
        """Ensure LLM service is initialized."""
        if self.llm_service is None:
            try:
                self.llm_service = get_llm_service()
                logger.info("[REPORT] LLM service initialized")
            except Exception as e:
                logger.error(f"[REPORT] Failed to initialize LLM service: {e}")
                raise

    async def analyze_cluster(
        self,
        cluster_label: str,
        ideas: List[Dict[str, Any]],
        session_theme: str,
        participant_count: int,
    ) -> str:
        """
        Analyze a cluster using LLM.

        Args:
            cluster_label: Name of the cluster
            ideas: List of ideas in the cluster (with formatted_text, novelty_score, user_name)
            session_theme: Theme of the session
            participant_count: Number of participants

        Returns:
            LLM-generated analysis text
        """
        await self._ensure_llm_service()

        if not ideas:
            return "このクラスタにはアイディアがありません。"

        # Randomly sample up to 50 ideas
        import random
        sample_size = min(50, len(ideas))
        sampled_ideas = random.sample(ideas, sample_size)

        # Build ideas list (without scores)
        ideas_list_lines = []
        for i, idea in enumerate(sampled_ideas, 1):
            ideas_list_lines.append(
                f"{i}. {idea['formatted_text']} (投稿者: {idea['user_name']})"
            )
        ideas_list = "\n".join(ideas_list_lines)

        # Build prompt
        prompt = CLUSTER_ANALYSIS_PROMPT.format(
            cluster_label=cluster_label,
            idea_count=len(ideas),
            session_theme=session_theme,
            participant_count=participant_count,
            ideas_list=ideas_list,
        )

        try:
            analysis = await self.llm_service.provider.generate(
                prompt,
                temperature=0.7,
            )
            logger.info(f"[REPORT] Generated analysis for cluster: {cluster_label} (sampled {sample_size}/{len(ideas)} ideas)")
            return analysis
        except Exception as e:
            logger.error(f"[REPORT] Failed to analyze cluster {cluster_label}: {e}")
            return f"クラスタの分析中にエラーが発生しました: {str(e)}"

    async def generate_overall_conclusion(
        self,
        session_theme: str,
        participant_count: int,
        total_ideas: int,
        cluster_count: int,
        cluster_insights: List[Dict[str, Any]],
    ) -> str:
        """
        Generate overall conclusion using LLM.

        Args:
            session_theme: Theme of the session
            participant_count: Number of participants
            total_ideas: Total number of ideas
            cluster_count: Number of clusters
            cluster_insights: List of cluster insights with label and analysis

        Returns:
            LLM-generated overall conclusion
        """
        await self._ensure_llm_service()

        # Build cluster insights summary
        insights_lines = []
        for i, insight in enumerate(cluster_insights, 1):
            insights_lines.append(f"【テーマ{i}: {insight['label']}】")
            insights_lines.append(f"アイディア数: {insight['idea_count']}件")
            # Add first 300 chars of analysis as summary
            analysis_preview = insight['analysis'][:300] + "..." if len(insight['analysis']) > 300 else insight['analysis']
            insights_lines.append(f"分析: {analysis_preview}")
            insights_lines.append("")

        cluster_insights_summary = "\n".join(insights_lines)

        # Build prompt
        prompt = OVERALL_CONCLUSION_PROMPT.format(
            session_theme=session_theme,
            participant_count=participant_count,
            total_ideas=total_ideas,
            cluster_count=cluster_count,
            cluster_insights_summary=cluster_insights_summary,
        )

        try:
            conclusion = await self.llm_service.provider.generate(
                prompt,
                temperature=0.7,
            )
            logger.info("[REPORT] Generated overall conclusion")
            return conclusion
        except Exception as e:
            logger.error(f"[REPORT] Failed to generate overall conclusion: {e}")
            return f"全体総括の生成中にエラーが発生しました: {str(e)}"
