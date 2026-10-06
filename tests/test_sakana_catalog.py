"""Offline checks for the Sakana AI page catalog. No network."""

from __future__ import annotations

import ast
import copy
import json
import re
import socket
from pathlib import Path

import pytest

import pdoom_pipeline.catalogs.sakana as sakana
from pdoom_pipeline.catalogs.sakana import (
    CATALOG_ID,
    OFFICIAL_HOST,
    PUBLISHER,
    RIGHTS_APACHE,
    RIGHTS_CC_BY_NC,
    RIGHTS_CC_BY_NC_ND,
    RIGHTS_CC_BY_NC_SA,
    RIGHTS_CC_BY_ND,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_CREATIVE_COMMONS_ATTRIBUTION,
    RIGHTS_MIT,
    RIGHTS_MPL,
    RIGHTS_UK_OGL,
    RIGHTS_UNKNOWN,
    RIGHTS_US_GOVERNMENT_WORK,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    catalog_path,
    confirmed_fetch_url,
    is_challenge_page,
    load_catalog,
    official_sakana_host,
    page_record,
    publication_date_from_page,
    record_from_response,
    rights_from_page,
    robots_allows,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

# Titles, publishers, canonical URLs, dates, and rights confirmed from one bounded GET each.
# The blog index lists many posts, so it has no single publication date.
# rsi-lab and the older about page did not state a publication date.
# Four pages state Apache-2.0 for software they release or train from. The rest state no reuse licence.
EXPECTED = [
    [
        "We raised $30M to develop nature-inspired AI in Japan",
        "Sakana AI",
        "https://sakana.ai/seed-round/",
        "2024-01-16",
        "unknown"
    ],
    [
        "We received a supercomputing grant from the Japanese government",
        "Sakana AI",
        "https://sakana.ai/nedo-grant/",
        "2024-02-02",
        "unknown"
    ],
    [
        "進化的アルゴリズムによる基盤モデルの構築",
        "Sakana AI",
        "https://sakana.ai/evolutionary-model-merge-jp/",
        "2024-03-21",
        "unknown"
    ],
    [
        "Evolving New Foundation Models: Unleashing the Power of Automating Model Development",
        "Sakana AI",
        "https://sakana.ai/evolutionary-model-merge/",
        "2024-03-21",
        "unknown"
    ],
    [
        "画像生成モデルへの進化的モデルマージの適用 日本語対応した高速な画像生成モデルを教育目的で公開",
        "Sakana AI",
        "https://sakana.ai/evosdxl-jp/",
        "2024-04-22",
        "unknown"
    ],
    [
        "Can LLMs invent better ways to train LLMs?",
        "Sakana AI",
        "https://sakana.ai/llm-squared/",
        "2024-06-13",
        "unknown"
    ],
    [
        "日本の美を学んだAI：浮世絵風画像生成モデルEvo-Ukiyoeと浮世絵カラー化モデルEvo-Nishikieを公開",
        "Sakana AI",
        "https://sakana.ai/evo-ukiyoe/",
        "2024-07-21",
        "unknown"
    ],
    [
        "進化的モデルマージによる視覚言語モデルの新たな能力の獲得 複数の画像を扱える日本語視覚言語モデルを公開",
        "Sakana AI",
        "https://sakana.ai/evovlm-jp/",
        "2024-08-02",
        "unknown"
    ],
    [
        "「AIサイエンティスト」： AIが自ら研究する時代へ",
        "Sakana AI",
        "https://sakana.ai/ai-scientist-jp/",
        "2024-08-13",
        "unknown"
    ],
    [
        "The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery",
        "Sakana AI",
        "https://sakana.ai/ai-scientist/",
        "2024-08-13",
        "unknown"
    ],
    [
        "Announcing Our Series A",
        "Sakana AI",
        "https://sakana.ai/series-a/",
        "2024-09-04",
        "unknown"
    ],
    [
        "シリーズA【続報】：日本のリーディングカンパニーから資金を調達、日本市場での事業展開を加速",
        "Sakana AI",
        "https://sakana.ai/series-a-jp/",
        "2024-09-17",
        "unknown"
    ],
    [
        "多様性を重視した集団ベースのモデルマージ",
        "Sakana AI",
        "https://sakana.ai/cycleqd-jp/",
        "2024-12-03",
        "unknown"
    ],
    [
        "Population-based Model Merging via Quality Diversity",
        "Sakana AI",
        "https://sakana.ai/cycleqd/",
        "2024-12-03",
        "unknown"
    ],
    [
        "An Evolved Universal Transformer Memory",
        "Sakana AI",
        "https://sakana.ai/namm/",
        "2024-12-10",
        "unknown"
    ],
    [
        "Automating the Search for Artificial Life with Foundation Models",
        "Sakana AI",
        "https://sakana.ai/asal/",
        "2024-12-24",
        "unknown"
    ],
    [
        "Transformer²: Self-Adaptive LLMs",
        "Sakana AI",
        "https://sakana.ai/transformer-squared/",
        "2025-01-15",
        "unknown"
    ],
    [
        "新手法「TAID」を用いた小規模日本語言語モデル「TinySwallow-1.5B」の公開",
        "Sakana AI",
        "https://sakana.ai/taid-jp/",
        "2025-01-30",
        "unknown"
    ],
    [
        "TAID: A Novel Method for Efficient Knowledge Transfer from Large Language Models to Small Language Models",
        "Sakana AI",
        "https://sakana.ai/taid/",
        "2025-02-25",
        "unknown"
    ],
    [
        "サカナの論文ミス CEOが語る勇み足とAIのごまかし問題",
        "Sakana AI",
        "https://sakana.ai/ai-cuda-engineer-post-mortem/",
        "2025-03-03",
        "unknown"
    ],
    [
        "Sakana AI「事業開発本部」を立ち上げ：AI技術のビジネス展開に着手",
        "Sakana AI",
        "https://sakana.ai/business-team/",
        "2025-03-04",
        "unknown"
    ],
    [
        "The AI Scientist Generates its First Peer-Reviewed Scientific Publication",
        "Sakana AI",
        "https://sakana.ai/ai-scientist-first-publication/",
        "2025-03-12",
        "unknown"
    ],
    [
        "世界初、100%AI生成の論文が査読通過 「AIサイエンティスト」が達成",
        "Sakana AI",
        "https://sakana.ai/ai-scientist-first-publication-jp/",
        "2025-03-13",
        "unknown"
    ],
    [
        "Sakana AI super-powers AI reasoning using Japan’s own Sudoku Puzzles",
        "Sakana AI",
        "https://sakana.ai/sudoku-bench/",
        "2025-03-21",
        "unknown"
    ],
    [
        "Sakana AI、防衛イノベーションの日米コンペティションで受賞",
        "Sakana AI",
        "https://sakana.ai/defense-challenge-2025-jp/",
        "2025-03-24",
        "unknown"
    ],
    [
        "Sakana AI Wins Award at US-Japan Competition for Defense Innovation",
        "Sakana AI",
        "https://sakana.ai/defense-challenge-2025/",
        "2025-03-24",
        "unknown"
    ],
    [
        "江戸時代の古文風テキストで会話できるチャットボット「からまる」を公開：過去の書物の継続学習による大規模言語モデルの開発",
        "Sakana AI",
        "https://sakana.ai/karamaru/",
        "2025-04-01",
        "unknown"
    ],
    [
        "Sakana AIで働く研究者インタビュー（2025年3月メディア掲載）",
        "Sakana AI",
        "https://sakana.ai/cv-interview-2025/",
        "2025-04-04",
        "unknown"
    ],
    [
        "「時間を使って考える」AIの新パラダイム、Continuous Thought Machine（CTM）を提案",
        "Sakana AI",
        "https://sakana.ai/ctm-jp/",
        "2025-05-12",
        "unknown"
    ],
    [
        "Introducing Continuous Thought Machines",
        "Sakana AI",
        "https://sakana.ai/ctm/",
        "2025-05-12",
        "unknown"
    ],
    [
        "Announcing a Multiyear Partnership between Sakana AI and MUFG Bank",
        "Sakana AI",
        "https://sakana.ai/mufg-bank/",
        "2025-05-19",
        "unknown"
    ],
    [
        "Sakana AI、三菱UFJ銀行と今後数年にわたる包括的パートナーシップ契約締結",
        "Sakana AI",
        "https://sakana.ai/mufg/",
        "2025-05-19",
        "unknown"
    ],
    [
        "AIの創造的な推論力を測る：Sudoku-Benchリーダーボード公開",
        "Sakana AI",
        "https://sakana.ai/sudoku-bench-jp/",
        "2025-05-26",
        "unknown"
    ],
    [
        "自らのコードを書き換え自己改善するAI：「ダーウィン・ゲーデルマシン」（DGM）の提案",
        "Sakana AI",
        "https://sakana.ai/dgm-jp/",
        "2025-05-30",
        "unknown"
    ],
    [
        "The Darwin Gödel Machine: AI that improves itself by rewriting its own code",
        "Sakana AI",
        "https://sakana.ai/dgm/",
        "2025-05-30",
        "unknown"
    ],
    [
        "EDINET-Bench: 有価証券報告書を用いた日本語金融ベンチマークの公開",
        "Sakana AI",
        "https://sakana.ai/edinet-bench/",
        "2025-06-09",
        "unknown"
    ],
    [
        "Sakana AI、北國フィナンシャルホールディングスと戦略提携 地域金融×AIの推進に向けたMOUを締結",
        "Sakana AI",
        "https://sakana.ai/hokkokubank/",
        "2025-06-10",
        "unknown"
    ],
    [
        "Text-to-LoRA: Instant Transformer Adaption",
        "Sakana AI",
        "https://sakana.ai/text-to-lora/",
        "2025-06-12",
        "unknown"
    ],
    [
        "実用的なアルゴリズムエンジニアリングの自動化へ：ALE-BenchおよびALE-Agentの開発",
        "Sakana AI",
        "https://sakana.ai/ale-bench-jp/",
        "2025-06-17",
        "unknown"
    ],
    [
        "Towards Automating Long-Horizon Algorithm Engineering for Hard Optimization Problems",
        "Sakana AI",
        "https://sakana.ai/ale-bench/",
        "2025-06-17",
        "unknown"
    ],
    [
        "Reinforcement Learning Teachers of Test Time Scaling",
        "Sakana AI",
        "https://sakana.ai/rlt/",
        "2025-06-23",
        "unknown"
    ],
    [
        "「集合知」と「試行錯誤」によるフロンティアAIの推論時スケーリング",
        "Sakana AI",
        "https://sakana.ai/ab-mcts-jp/",
        "2025-07-01",
        "apache-2.0"
    ],
    [
        "Inference-Time Scaling and Collective Intelligence for Frontier AI",
        "Sakana AI",
        "https://sakana.ai/ab-mcts/",
        "2025-07-01",
        "apache-2.0"
    ],
    [
        "最先端のAI技術をビジネスへ：Sakana AI、Applied Teamメンバーインタビュー",
        "Sakana AI",
        "https://sakana.ai/applied-team-interview-2025/",
        "2025-07-29",
        "unknown"
    ],
    [
        "【イベントレポート】Applied Research Engineer Open House 2025：金融・防衛の難関課題に挑む、AI社会実装の最前線",
        "Sakana AI",
        "https://sakana.ai/open-house-2025/",
        "2025-08-14",
        "unknown"
    ],
    [
        "Competition and Attraction Improve Model Fusion",
        "Sakana AI",
        "https://sakana.ai/m2n2/",
        "2025-08-25",
        "unknown"
    ],
    [
        "AI CUDA Engineer続報：堅牢なベンチマークの構築と中間報告",
        "Sakana AI",
        "https://sakana.ai/ai-cuda-engineer-update/",
        "2025-09-17",
        "unknown"
    ],
    [
        "ShinkaEvolve: Evolving New Algorithms with LLMs, Orders of Magnitude More Efficiently",
        "Sakana AI",
        "https://sakana.ai/shinka-evolve/",
        "2025-09-25",
        "apache-2.0"
    ],
    [
        "Sakana AI and Daiwa Securities Group to Develop AI for Advanced Asset Consulting",
        "Sakana AI",
        "https://sakana.ai/daiwa-securities/",
        "2025-10-03",
        "unknown"
    ],
    [
        "Sakana AI、大和証券グループと総資産コンサルティング高度化AIの開発へ",
        "Sakana AI",
        "https://sakana.ai/daiwa-shoken/",
        "2025-10-03",
        "unknown"
    ],
    [
        "ShinkaEvolve in Action: How a Human-AI Partnership Conquered a Coding Challenge",
        "Sakana AI",
        "https://sakana.ai/icfp-2025/",
        "2025-10-16",
        "unknown"
    ],
    [
        "採用候補者向け Sakana AI Applied Team 紹介",
        "Sakana AI",
        "https://sakana.ai/applied-team-intro/",
        "2025-10-30",
        "unknown"
    ],
    [
        "Applied Team メンバー紹介",
        "Sakana AI",
        "https://sakana.ai/applied-team-profiles/",
        "2025-10-30",
        "unknown"
    ],
    [
        "Petri Dish Neural Cellular Automata",
        "Sakana AI",
        "https://sakana.ai/pd-nca/",
        "2025-11-05",
        "unknown"
    ],
    [
        "Announcing Our Series B",
        "Sakana AI",
        "https://sakana.ai/series-b/",
        "2025-11-17",
        "unknown"
    ],
    [
        "AIを駆使してAI実装を加速する：Sakana AI、Software Engineerインタビュー",
        "Sakana AI",
        "https://sakana.ai/swe-interview-2025/",
        "2025-11-19",
        "unknown"
    ],
    [
        "AIエージェントが最適化プログラミングコンテストで初優勝",
        "Sakana AI",
        "https://sakana.ai/ahc-2025/",
        "2025-12-23",
        "unknown"
    ],
    [
        "Sakana AI Agent Wins AtCoder Heuristic Contest (First AI to Place 1st)",
        "Sakana AI",
        "https://sakana.ai/ahc058/",
        "2026-01-05",
        "unknown"
    ],
    [
        "Digital Red Queen: Adversarial Program Evolution in Core War with LLMs",
        "Sakana AI",
        "https://sakana.ai/drq/",
        "2026-01-08",
        "unknown"
    ],
    [
        "Extending the Context of Pretrained LLMs by Dropping Their Positional Embeddings",
        "Sakana AI",
        "https://sakana.ai/drope/",
        "2026-01-12",
        "unknown"
    ],
    [
        "RePo: Language Models with Context Re-Positioning",
        "Sakana AI",
        "https://sakana.ai/repo/",
        "2026-01-19",
        "unknown"
    ],
    [
        "An Unofficial Guide to Prepare for a Research Position Application",
        "Sakana AI",
        "https://sakana.ai/unofficial-guide/",
        "2026-01-20",
        "unknown"
    ],
    [
        "Sakana AI、Googleとの戦略的パートナーシップ締結を発表",
        "Sakana AI",
        "https://sakana.ai/google/",
        "2026-01-23",
        "unknown"
    ],
    [
        "オフィス移転のお知らせ",
        "Sakana AI",
        "https://sakana.ai/azabudai-hills/",
        "2026-02-16",
        "unknown"
    ],
    [
        "Salesforce Ventures invests in Sakana AI",
        "Sakana AI",
        "https://sakana.ai/salesforce-ventures/",
        "2026-02-19",
        "unknown"
    ],
    [
        "Announcing a Strategic Investment from Citi",
        "Sakana AI",
        "https://sakana.ai/citi/",
        "2026-02-24",
        "unknown"
    ],
    [
        "Announcing a Strategic Partnership with Datadog",
        "Sakana AI",
        "https://sakana.ai/datadog/",
        "2026-02-26",
        "unknown"
    ],
    [
        "Instant LLM Updates with Doc-to-LoRA and Text-to-LoRA",
        "Sakana AI",
        "https://sakana.ai/doc-to-lora/",
        "2026-02-27",
        "unknown"
    ],
    [
        "MUFGとSakana AIの「AI融資エキスパート」、実案件での検証フェーズへ",
        "Sakana AI",
        "https://sakana.ai/mufg-ai-lending/",
        "2026-03-06",
        "unknown"
    ],
    [
        "Sakana AI、防衛イノベーション科学技術研究所からの委託研究を開始",
        "Sakana AI",
        "https://sakana.ai/atla-contract-2026/",
        "2026-03-13",
        "unknown"
    ],
    [
        "【Sakana AI Applied Case Interview】銀行業務へのAIエージェント実装に向けた開発の舞台裏",
        "Sakana AI",
        "https://sakana.ai/mufg-ai-lending-interview/",
        "2026-03-19",
        "unknown"
    ],
    [
        "【読売新聞】Sakana AIの独自システムがSNS上の「認知戦」を可視化",
        "Sakana AI",
        "https://sakana.ai/narrative-intelligence/",
        "2026-03-23",
        "unknown"
    ],
    [
        "最大規模のオープン基盤モデルを各国仕様へ適応させる事後学習技術を開発",
        "Sakana AI",
        "https://sakana.ai/namazu-alpha/",
        "2026-03-24",
        "unknown"
    ],
    [
        "AIによるAI研究の実現へ：AIサイエンティスト論文がNature誌に掲載",
        "Sakana AI",
        "https://sakana.ai/ai-scientist-nature-jp/",
        "2026-03-26",
        "unknown"
    ],
    [
        "The AI Scientist: Towards Fully Automated AI Research, Now Published in Nature",
        "Sakana AI",
        "https://sakana.ai/ai-scientist-nature/",
        "2026-03-26",
        "unknown"
    ],
    [
        "新しいBusiness Intelligenceへ：Ultra Deep Researchアシスタント「Sakana Marlin」βテスト開始",
        "Sakana AI",
        "https://sakana.ai/marlin-beta/",
        "2026-04-02",
        "unknown"
    ],
    [
        "Sakana AI、総務省事業においてSNS空間の可視化と偽・誤情報対策を行う独自技術を開発",
        "Sakana AI",
        "https://sakana.ai/mic-project/",
        "2026-04-07",
        "unknown"
    ],
    [
        "Digital Ecosystems: Interactive Multi-Agent Neural Cellular Automata",
        "Sakana AI",
        "https://sakana.ai/digital-ecosystem/",
        "2026-04-19",
        "unknown"
    ],
    [
        "String Seed of Thought: Prompting LLMs for Distribution-Faithful and Diverse Generation",
        "Sakana AI",
        "https://sakana.ai/ssot/",
        "2026-04-21",
        "unknown"
    ],
    [
        "Sakana Fugu: A Multi-Agent Orchestration System as a Foundation Model",
        "Sakana AI",
        "https://sakana.ai/fugu-beta/",
        "2026-04-24",
        "unknown"
    ],
    [
        "Trinity: An Evolved LLM Coordinator",
        "Sakana AI",
        "https://sakana.ai/trinity/",
        "2026-04-26",
        "unknown"
    ],
    [
        "Learning to Orchestrate Agents in Natural Language with the Conductor",
        "Sakana AI",
        "https://sakana.ai/learning-to-orchestrate/",
        "2026-04-27",
        "unknown"
    ],
    [
        "KAME: Tandem Architecture for Enhancing Knowledge in Real-Time Speech-to-Speech Conversational AI",
        "Sakana AI",
        "https://sakana.ai/kame-icassp-2026/",
        "2026-04-29",
        "unknown"
    ],
    [
        "Sakana AI、SMBCグループと共同で複数AIエージェントを活用する「提案書自動生成アプリケーション」を開発",
        "Sakana AI",
        "https://sakana.ai/smbc-proposal-ai/",
        "2026-04-30",
        "unknown"
    ],
    [
        "Sparser, Faster, Lighter Transformer Language Models",
        "Sakana AI",
        "https://sakana.ai/twell/",
        "2026-05-09",
        "unknown"
    ],
    [
        "防衛分野における開発の最前線：Sakana AI、Software Engineerインタビュー",
        "Sakana AI",
        "https://sakana.ai/defense-swe-interview-2026/",
        "2026-05-11",
        "unknown"
    ],
    [
        "DiffusionBlocks: Training Neural Networks One Block at a Time",
        "Sakana AI",
        "https://sakana.ai/diffusion-blocks/",
        "2026-05-28",
        "unknown"
    ],
    [
        "Sakana AI、一般社団法人DEEP DIVEとAIを活用した情報分析に関するパートナーシップを締結",
        "Sakana AI",
        "https://sakana.ai/deep-dive-partnership/",
        "2026-05-29",
        "unknown"
    ],
    [
        "金融領域の業務をAIエージェントで変える：Sakana AI、Software Engineerインタビュー",
        "Sakana AI",
        "https://sakana.ai/finance-swe-interview-2026/",
        "2026-06-01",
        "unknown"
    ],
    [
        "Sakana AI、初の商用プロダクト「Sakana Marlin」を提供開始",
        "Sakana AI",
        "https://sakana.ai/marlin-release/",
        "2026-06-15",
        "unknown"
    ],
    [
        "Sakana Fugu: One Model to Command Them All",
        "Sakana AI",
        "https://sakana.ai/fugu-release/",
        "2026-06-22",
        "unknown"
    ],
    [
        "CoffeeBench: マルチエージェント経済環境におけるLLMエージェントの長期タスクベンチマーク",
        "Sakana AI",
        "https://sakana.ai/coffee-bench/",
        "2026-06-26",
        "unknown"
    ],
    [
        "Sakana AI 伊藤錬、国連「AI for Good」グローバル委員会創設委員に就任",
        "Sakana AI",
        "https://sakana.ai/ai-for-good-commission/",
        "2026-07-03",
        "unknown"
    ],
    [
        "Bridging Spherical Black-Box Optimizers",
        "Sakana AI",
        "https://sakana.ai/bbob/",
        "2026-07-04",
        "unknown"
    ],
    [
        "Learning Multi-Agent Coordination via Sheaf-ADMM",
        "Sakana AI",
        "https://sakana.ai/sheaf-admm/",
        "2026-07-05",
        "unknown"
    ],
    [
        "Sakana Translate：Sakana Chatが翻訳に対応、翻訳・添削・質疑の3機能を搭載",
        "Sakana AI",
        "https://sakana.ai/translate-release/",
        "2026-07-06",
        "unknown"
    ],
    [
        "The AI Picbreeder Experiment: Can AI agents be creative when nobody tells them what to create?",
        "Sakana AI",
        "https://sakana.ai/picbreeder-ai/",
        "2026-07-10",
        "unknown"
    ],
    [
        "Smart Cellular Bricks: Towards Collective Intelligence for the Physical World",
        "Sakana AI",
        "https://sakana.ai/smart-cellular-bricks/",
        "2026-07-13",
        "unknown"
    ],
    [
        "Sakana AI Teams With NVIDIA to Advance Open Model Innovation from Japan",
        "Sakana AI",
        "https://sakana.ai/nvidia-open-model-innovation/",
        "2026-07-16",
        "unknown"
    ],
    [
        "Introducing Fugu-Cyber: our new orchestration model that achieves state-of-the-art performance on real-world cybersecurity benchmarks",
        "Sakana AI",
        "https://sakana.ai/fugu-cyber-release/",
        "2026-07-21",
        "unknown"
    ],
    [
        "UnMaskFork: Test-Time Scaling for Masked Diffusion via Deterministic Action Branching",
        "Sakana AI",
        "https://sakana.ai/umf/",
        "2026-07-23",
        "unknown"
    ],
    [
        "Announcing Fugu-Ultra v1.1 and Claude Code interface for Fugu",
        "Sakana AI",
        "https://sakana.ai/fugu-1-1-claude-code-interface/",
        "2026-07-24",
        "unknown"
    ],
    [
        "Dreaming in Voxels: How AI is Generating Playable Minecraft Worlds",
        "Sakana AI",
        "https://sakana.ai/dream-cubed/",
        "2026-07-29",
        "unknown"
    ],
    [
        "Sakana AI防衛・インテリジェンスチーム、「DIVER OSINT CTF 2026」で5位入賞 Fuguを活用したOSINTエージェントの可能性",
        "Sakana AI",
        "https://sakana.ai/diver-osint/",
        "2026-07-30",
        "unknown"
    ],
    [
        "From Japan, Products the World Will Use: An Interview with Sakana AI's Head of Product Development",
        "Sakana AI",
        "https://sakana.ai/product-development-interview/",
        "2026-07-31",
        "unknown"
    ],
    [
        "Sakana AI、日本語特化のLLM API「Sakana Namazu」を提供開始",
        "Sakana AI",
        "https://sakana.ai/namazu-api/",
        "2026-08-03",
        "unknown"
    ],
    [
        "Sakana AI、大和証券グループとの共同AIプロジェクトを本格展開フェーズへ移行 ウェルスマネジメント業務支援AIの開発を開始",
        "Sakana AI",
        "https://sakana.ai/daiwa-shoken-full-scale/",
        "2026-08-05",
        "unknown"
    ],
    [
        "ベースモデルに依存しないオーケストレーションに向けて：Gemma 4版 Sakana Fuguの検証",
        "Sakana AI",
        "https://sakana.ai/fugu-gemma4/",
        "2026-08-10",
        "apache-2.0"
    ],
    [
        "Sakana Chatがアップデート：「Sakana Fugu」と新世代「Sakana Namazu」が利用可能に",
        "Sakana AI",
        "https://sakana.ai/chat-update/",
        "2026-08-13",
        "unknown"
    ],
    [
        "Sakana Translateをアップデート：翻訳モデルに新世代「Sakana Namazu」を搭載",
        "Sakana AI",
        "https://sakana.ai/translate-update/",
        "2026-08-21",
        "unknown"
    ],
    [
        "Sakana AI、防衛省から「総合分析業務に必要なAI機能の調査・実証」を受注",
        "Sakana AI",
        "https://sakana.ai/defense-integrated-analysis/",
        "2026-08-24",
        "unknown"
    ],
    [
        "Percept-Lens: A Deep Dive into AI-Generated Image Detection",
        "Sakana AI",
        "https://sakana.ai/percept-lens/",
        "2026-09-03",
        "unknown"
    ],
    [
        "Sakana AI、ＳＣＳＫ、住友商事の3社、AI活用による日本の産業変革と社会課題解決に向け包括業務提携 ～日本発の技術力・完遂力を核に、AIの社会実装を加速～",
        "Sakana AI",
        "https://sakana.ai/scsk-sc-partnership/",
        "2026-09-10",
        "unknown"
    ],
    [
        "Introducing Fugu Max and Fugu Ultra v2: Orchestrating the Pareto Frontier",
        "Sakana AI",
        "https://sakana.ai/fugu-max-release/",
        "2026-09-11",
        "unknown"
    ],
    [
        "英国王立協会特集号に見る、世界モデルの最前線とAIの未来",
        "Sakana AI",
        "https://sakana.ai/world-models-royal-society-issue/",
        "2026-09-12",
        "unknown"
    ],
    [
        "Training 1000-layer networks without backpropagation",
        "Sakana AI",
        "https://sakana.ai/pc-alm/",
        "2026-09-14",
        "unknown"
    ],
    [
        "Sakana Marlinアップデート：レポートと対話する「Interactive Reading」と、出力スライドのPowerPoint対応",
        "Sakana AI",
        "https://sakana.ai/marlin-update/",
        "2026-09-16",
        "unknown"
    ],
    [
        "Sakana Chatをアップデート：最新モデルに刷新、メモリー機能を追加",
        "Sakana AI",
        "https://sakana.ai/chat-fugumax/",
        "2026-09-17",
        "unknown"
    ],
    [
        "Inside Sakana AI's Product Team",
        "Sakana AI",
        "https://sakana.ai/inside-product-team/",
        "2026-09-17",
        "unknown"
    ],
    [
        "Introducing Sakana AI's Frontier Intelligence Group (FIG)",
        "Sakana AI",
        "https://sakana.ai/frontier-intelligence-group/",
        "2026-09-18",
        "unknown"
    ],
    [
        "The Next Frontier: Welcoming AI Pioneer Jürgen Schmidhuber to Sakana AI",
        "Sakana AI",
        "https://sakana.ai/schmidhuber/",
        "2026-09-24",
        "unknown"
    ],
    [
        "Sakana AI、「日本スタートアップ大賞2026」で総務大臣賞（情報通信分野）を受賞",
        "Sakana AI",
        "https://sakana.ai/japan-startup-award-2026/",
        "2026-09-25",
        "unknown"
    ],
    [
        "SAIL: Scaling In-Context Imitation Learning",
        "Sakana AI",
        "https://sakana.ai/sail/",
        "2026-09-28",
        "unknown"
    ],
    [
        "Sakana AI Blog",
        "Sakana AI",
        "https://sakana.ai/blog/",
        "unknown",
        "unknown"
    ],
    [
        "About Sakana AI",
        "Sakana AI",
        "https://sakana.ai/company-info-old/",
        "unknown",
        "unknown"
    ],
    [
        "AIがAIを作る：Sakana AI「RSI Lab」始動",
        "Sakana AI",
        "https://sakana.ai/rsi-lab-jp/",
        "unknown",
        "unknown"
    ],
    [
        "Introducing Sakana AI’s Recursive Self-Improvement (RSI) Lab",
        "Sakana AI",
        "https://sakana.ai/rsi-lab/",
        "unknown",
        "unknown"
    ]
]

SAMPLE_URL = "https://sakana.ai/sail/"
BODY = (
    "We propose SAIL, a method for more reliable VLM-based robot trajectory "
    "generation through test-time scaling. This paragraph is not catalog metadata."
)
REJECTED_URLS = [
    "http://sakana.ai/blog/",
    "https://www.sakana.ai/blog/",
    "https://pub.sakana.ai/",
    "https://pub.sakana.ai/sail/",
    "https://chat.sakana.ai/",
    "https://translate.sakana.ai/",
    "https://console.sakana.ai/login",
    "https://arxiv.org/abs/2603.08269",
    "https://sakana.ai/blog/?label=research",
    "https://sakana.ai/blog/#research",
    "https://sakana.ai/login/",
    "https://sakana.ai/console/",
    "https://user:pass@sakana.ai/blog/",
    "https://sakana.ai:443/blog/",
    "https://sakana.ai/feed.xml",
    "https://sakana.ai/paper.pdf",
    "https://sakana.ai/blog",
    "https://127.0.0.1/blog/",
    "https://169.254.169.254/latest/meta-data/",
    "https://sakana.ai/blog/../sail/",
]
CLOUDFLARE_HTML = (
    "<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
    "<body>Checking your browser before accessing sakana.ai. "
    "cf-mitigated: challenge challenge-platform</body></html>"
)
SITEGROUND_HTML = (
    "<html><head><meta http-equiv=\"refresh\" "
    "content=\"0;/.well-known/sgcaptcha/?r=%2Fblog%2F\"></head>"
    "<body>sg-captcha</body></html>"
)
AKAMAI_HTML = (
    "<html><head><title>Access Denied</title></head>"
    "<body>You don't have permission to access. AkamaiGHost errors.edgesuite.net</body></html>"
)
ROBOTS_404 = "<!DOCTYPE html><html><title>404: Page not found</title><p>Page not found</p></html>"


def _page(title: str, canonical: str, *, published: str | None = None, updated: str | None = None) -> str:
    published_tag = (
        f'<meta property="article:published_time" content="{published}">' if published else ""
    )
    updated_tag = f'<meta property="article:modified_time" content="{updated}">' if updated else ""
    return (
        "<html><head>"
        f"<title>{title}</title>"
        '<meta name="author" content="Sakana AI">'
        f"{published_tag}{updated_tag}"
        f'<link rel="canonical" href="{canonical}">'
        "</head><body>"
        f"<h1>{title}</h1>"
        f"<p>{BODY}</p>"
        "<p>By David Ha.</p>"
        "<footer>&copy; Sakana AI</footer>"
        "</body></html>"
    )


def test_catalog_load_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("catalog load must not use the network")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    document = load_catalog()
    assert document["catalog_id"] == CATALOG_ID
    assert document["runner_wired"] is False
    assert len(document["entries"]) == len(EXPECTED)


def test_committed_catalog_matches_confirmed_pages():
    document = load_catalog()
    assert catalog_path().name == "sakana_pages.json"
    assert document["runner_wired"] is False
    assert RUNNER_WIRED is False
    description = document["description"]
    assert OFFICIAL_HOST in description
    assert "bounded GET" in description
    assert "robots.txt" in description
    assert "404" in description
    assert "creative_commons" in description
    assert "creative_commons_attribution" in description
    assert "runner_wired is false" in description
    assert "belief collector" in description
    assert len(description) <= 800
    raw = catalog_path().read_text(encoding="utf-8")
    for host in (
        "pub.sakana.ai",
        "chat.sakana.ai",
        "translate.sakana.ai",
        "console.sakana.ai",
        "www.sakana.ai",
        "arxiv.org",
    ):
        assert host not in raw
    assert "<html" not in raw.casefold()
    assert ".pdf" not in raw.casefold()
    assert BODY not in raw
    parsed = json.loads(raw)
    assert set(parsed) == {"catalog_id", "description", "runner_wired", "entries"}
    entries = document["entries"]
    assert [
        tuple(entry[field] for field in ("title", "publisher", "canonical_url", "date", "rights"))
        for entry in entries
    ] == [tuple(row) for row in EXPECTED]
    rights_counts = {label: 0 for label in (
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_CREATIVE_COMMONS_ATTRIBUTION,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_UK_OGL,
        RIGHTS_US_GOVERNMENT_WORK,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_MPL,
    )}
    unknown_dates = 0
    forbidden = {"abstract", "body", "chart", "chart_data", "quote", "transcript", "page_text"}
    for entry in entries:
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert forbidden.isdisjoint(entry)
        assert entry["publisher"] == PUBLISHER
        assert entry["canonical_url"].startswith("https://sakana.ai/")
        assert official_sakana_host(entry["canonical_url"].split("/")[2])
        assert entry["date"] == UNKNOWN_DATE or re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"])
        rights_counts[entry["rights"]] += 1
        if entry["date"] == UNKNOWN_DATE:
            unknown_dates += 1
    assert len(entries) == 127
    assert rights_counts[RIGHTS_UNKNOWN] == 123
    assert rights_counts[RIGHTS_APACHE] == 4
    assert unknown_dates == 4
    assert sum(rights_counts.values()) == 127
    by_url = {entry["canonical_url"]: entry for entry in entries}
    assert by_url["https://sakana.ai/blog/"]["title"] == "Sakana AI Blog"
    assert by_url["https://sakana.ai/blog/"]["date"] == UNKNOWN_DATE
    assert by_url["https://sakana.ai/sail/"]["date"] == "2026-09-28"
    assert by_url["https://sakana.ai/sail/"]["rights"] == RIGHTS_UNKNOWN
    assert by_url["https://sakana.ai/ab-mcts/"]["rights"] == RIGHTS_APACHE
    assert by_url["https://sakana.ai/ab-mcts-jp/"]["rights"] == RIGHTS_APACHE
    assert by_url["https://sakana.ai/shinka-evolve/"]["rights"] == RIGHTS_APACHE
    assert by_url["https://sakana.ai/fugu-gemma4/"]["rights"] == RIGHTS_APACHE
    assert by_url["https://sakana.ai/company-info-old/"]["date"] == UNKNOWN_DATE
    assert by_url["https://sakana.ai/rsi-lab/"]["date"] == UNKNOWN_DATE
    nature = by_url["https://sakana.ai/ai-scientist-nature/"]
    assert nature["title"] == "The AI Scientist: Towards Fully Automated AI Research, Now Published in Nature"
    assert "<" not in nature["title"]


def test_sole_restricted_deeds_keep_their_tokens():
    assert rights_from_page("<p>CC BY-NC</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>cc-by-nc</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>Creative Commons Attribution-NonCommercial</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>CC BY-ND</p>") == RIGHTS_CC_BY_ND
    assert rights_from_page("<p>CC BY-NC-ND</p>") == RIGHTS_CC_BY_NC_ND
    assert rights_from_page("<p>CC BY-NC-SA</p>") == RIGHTS_CC_BY_NC_SA
    assert rights_from_page("<p>CC BY</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<p>CC BY</p>") != RIGHTS_CC_BY_NC
    source = Path(sakana.__file__).read_text(encoding="utf-8")
    assert "(?!-)" in source


def test_permissive_deeds_and_mixed_text():
    assert rights_from_page("<p>This work is licensed under CC BY 4.0.</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<p>This work is licensed under CC BY-SA 4.0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>This work is licensed under CC0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC0 and CC BY-SA 4.0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY 4.0 and CC0.</p>") == RIGHTS_CREATIVE_COMMONS
    mixed = "<p>This work is CC BY 4.0 and also CC BY-NC.</p>"
    assert rights_from_page(mixed) == RIGHTS_UNKNOWN
    both_urls = (
        '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
        '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC</a>'
    )
    assert rights_from_page(both_urls) == RIGHTS_UNKNOWN


def test_misleading_anchors_and_non_licences_stay_unknown():
    cases = [
        '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY</a>',
        '<a href="https://creativecommons.org/licenses/by-nd/4.0/">CC BY-SA</a>',
        '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY</a>',
        '<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">CC BY</a>',
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC BY</a>',
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC BY-SA</a>',
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC0</a>',
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">Public Domain Mark</a>',
        '<a href="https://creativecommons.org/licenses/">Creative Commons</a>',
        "<footer>© 2026 Sakana AI. All rights reserved.</footer>",
        "<p>This page is Public. See the terms. Hosted at sakana.ai.</p>",
        '<a href="https://sakana.ai/">Sakana AI</a>',
        "<script>CC BY 4.0</script><p>All rights reserved.</p>",
        "<!-- CC BY 4.0 --><p>All rights reserved.</p>",
    ]
    for html in cases:
        assert rights_from_page(html) == RIGHTS_UNKNOWN
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by-nc/4.0/">licence</a>') == RIGHTS_CC_BY_NC
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by/4.0/">licence</a>') == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page('<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>') == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page('<link rel="license" href="https://creativecommons.org/licenses/by-nc-nd/4.0/">') == RIGHTS_CC_BY_NC_ND


def test_software_licences_and_open_government_licence():
    assert rights_from_page("<p>MIT License</p>") == RIGHTS_MIT
    assert rights_from_page("<p>Apache License 2.0</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>under the Apache 2.0 license</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Apache 2.0ライセンス</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Mozilla Public License 2.0</p>") == RIGHTS_MPL
    assert rights_from_page("<p>MPL-2.0</p>") == RIGHTS_MPL
    assert rights_from_page("<p>Python, Apache Beam/Spark, and Kubernetes.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>A collaboration with MIT and NYU.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MIT License and Apache-2.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache-2.0 and CC BY-SA 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Open Government Licence v3.0</p>") == RIGHTS_UK_OGL
    assert rights_from_page("<p>Licensed under the Open Government License v3.0.</p>") == RIGHTS_UNKNOWN
    archives = '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">terms</a>'
    assert rights_from_page(archives) == RIGHTS_UNKNOWN
    rights_field = '<meta name="dc.rights" content="This is a work of the United States Government.">'
    assert rights_from_page(rights_field) == RIGHTS_US_GOVERNMENT_WORK
    assert rights_from_page("<p>This is a work of the United States Government.</p>") == RIGHTS_UNKNOWN


def test_publication_dates_ignore_updated_modified_and_copyright_years():
    stated = (
        '<time datetime="2026-09-28T00:00:00+09:00">September 28, 2026</time>'
        '<meta property="article:modified_time" content="2026-10-01T00:00:00Z">'
        '<meta property="og:updated_time" content="2026-11-01T00:00:00Z">'
        "<p>© 2024 Sakana AI</p>"
    )
    assert publication_date_from_page(stated) == "2026-09-28"
    listing = (
        '<time datetime="2026-01-01T00:00:00+09:00">January 1, 2026</time>'
        '<time datetime="2026-02-02T00:00:00+09:00">February 2, 2026</time>'
        '<meta property="article:published_time" content="2020-01-01T00:00:00Z">'
    )
    assert publication_date_from_page(listing) == UNKNOWN_DATE
    updated = "<p>Last update: May 2026.</p><p>Updated 2024-05-01</p><p>© 2020 Sakana AI</p>"
    assert publication_date_from_page(updated) == UNKNOWN_DATE
    modified = '<meta property="article:modified_time" content="2024-04-18T14:43:38.000Z">'
    assert publication_date_from_page(modified) == UNKNOWN_DATE
    meta_only = '<meta property="article:published_time" content="2024-03-21T00:00:00+09:00">'
    assert publication_date_from_page(meta_only) == "2024-03-21"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    assert validate_date("2024-03-21") == "2024-03-21"
    with pytest.raises(CatalogError, match="date"):
        validate_date("21 March 2024")
    with pytest.raises(CatalogError, match="date"):
        validate_date("2024-02-31")


def test_page_record_keeps_metadata_and_not_the_document_body():
    record = page_record(_page("SAIL: Scaling In-Context Imitation Learning", SAMPLE_URL), page_url=SAMPLE_URL)
    assert record["title"] == "SAIL: Scaling In-Context Imitation Learning"
    assert record["publisher"] == PUBLISHER
    assert record["canonical_url"] == SAMPLE_URL
    assert record["date"] == UNKNOWN_DATE
    assert record["rights"] == RIGHTS_UNKNOWN
    assert set(record) == {"title", "publisher", "canonical_url", "date", "rights"}
    stored = json.dumps(record)
    assert BODY not in stored
    assert "David Ha" not in stored
    dated = page_record(
        _page("SAIL: Scaling In-Context Imitation Learning", SAMPLE_URL, published="2026-09-28T00:00:00+09:00", updated="2026-10-01T00:00:00Z"),
        page_url=SAMPLE_URL,
    )
    assert dated["date"] == "2026-09-28"
    assert "2026-10-01" not in json.dumps(dated)


def test_a_different_canonical_link_does_not_replace_the_live_url():
    html = _page("SAIL: Scaling In-Context Imitation Learning", "https://pub.sakana.ai/sail/")
    record = page_record(html, page_url=SAMPLE_URL)
    assert record["canonical_url"] == SAMPLE_URL


def test_a_person_is_not_the_publisher():
    record = page_record(_page("SAIL: Scaling In-Context Imitation Learning", SAMPLE_URL), page_url=SAMPLE_URL)
    assert record["publisher"] == PUBLISHER
    missing = "<html><head><title>A note</title></head><body><h1>A note</h1><p>By David Ha.</p></body></html>"
    with pytest.raises(CatalogError, match="publisher"):
        page_record(missing, page_url=SAMPLE_URL)


def test_challenge_status_and_off_host_redirect_are_not_stored():
    assert is_challenge_page(CLOUDFLARE_HTML)
    assert is_challenge_page(SITEGROUND_HTML)
    assert record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=CLOUDFLARE_HTML,
        page_url=SAMPLE_URL,
        headers={"cf-mitigated": "challenge"},
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=SITEGROUND_HTML,
        page_url=SAMPLE_URL,
        headers={"sg-captcha": "challenge"},
    ) is None
    assert record_from_response(
        status=202,
        content_type="text/html; charset=UTF-8",
        page_html=_page("Blog", "https://sakana.ai/blog/"),
        page_url="https://sakana.ai/blog/",
    ) is None
    assert record_from_response(
        status=403,
        content_type="text/html",
        page_html=AKAMAI_HTML,
        page_url=SAMPLE_URL,
        headers={"server": "AkamaiGHost"},
    ) is None
    assert record_from_response(
        status=200,
        content_type="application/pdf",
        page_html="%PDF-1.7 synthetic",
        page_url=SAMPLE_URL,
    ) is None
    assert confirmed_fetch_url(SAMPLE_URL, "https://pub.sakana.ai/sail/") is None
    assert confirmed_fetch_url("https://sakana.ai/blog/", "https://sakana.ai/sail/") is None
    stored = record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=_page("SAIL: Scaling In-Context Imitation Learning", SAMPLE_URL, published="2026-09-28T00:00:00+09:00"),
        page_url=SAMPLE_URL,
        final_url=SAMPLE_URL,
    )
    assert stored is not None
    assert stored["canonical_url"] == SAMPLE_URL
    assert stored["date"] == "2026-09-28"
    assert BODY not in json.dumps(stored)


def test_robots_404_allows_research_paths_and_a_disallow_blocks_them():
    assert robots_allows(ROBOTS_404, "/blog/")
    assert robots_allows(ROBOTS_404, "/sail/")
    assert robots_allows("", "/sail/")
    blocked = "User-agent: *\nDisallow: /\n"
    assert robots_allows(blocked, "/blog/") is False
    assert robots_allows(blocked, "/sail/") is False
    private = "User-agent: *\nDisallow: /private/\nAllow: /sail/\n"
    assert robots_allows(private, "/blog/") is True
    assert robots_allows(private, "/sail/") is True
    assert robots_allows(private, "/private/draft/") is False


def test_non_sakana_urls_are_rejected():
    for rejected in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(rejected)


@pytest.mark.parametrize(
    "url",
    [
        "https://sakana.ai/",
        "https://sakana.ai/blog/",
        "https://sakana.ai/sail/",
        "https://sakana.ai/ai-scientist-nature/",
    ],
)
def test_official_sakana_urls_are_accepted(url: str):
    assert validate_canonical_url(url) == url
    assert official_sakana_host(url.split("/")[2])


def test_validator_rejects_bad_rights_and_accepts_an_empty_list():
    document = copy.deepcopy(load_catalog())
    document["entries"] = []
    validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["rights"] = RIGHTS_APACHE
    validate_catalog(document)
    document["entries"][0]["rights"] = "cc-by"
    with pytest.raises(CatalogError, match="rights"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["body"] = BODY
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["abstract"] = "a stored abstract"
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["quote"] = "a stored quote"
    with pytest.raises(CatalogError):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"].append(dict(document["entries"][0]))
    with pytest.raises(CatalogError, match="duplicate canonical URL"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["canonical_url"] = "https://pub.sakana.ai/sail/"
    with pytest.raises(CatalogError):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0], document["entries"][1] = document["entries"][1], document["entries"][0]
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)


def test_catalog_is_not_wired_into_belief_collection():
    module = Path(sakana.__file__).read_text(encoding="utf-8")
    tree = ast.parse(module)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "requests" not in imported
    assert "pdoom_pipeline.fetch" not in imported
    assert "pdoom_pipeline.belief" not in imported
    assert "pdoom_pipeline.belief.collect" not in imported
    assert not re.search(r"(?m)^\s*(?:import|from)\s+requests\b", module)
    assert "hostname_is_blocked" in module
    assert "runner_wired = True" not in module

    root = Path(__file__).resolve().parents[1]
    init = (root / "pipeline" / "pdoom_pipeline" / "catalogs" / "__init__.py").read_text(encoding="utf-8")
    assert init.strip() == '"""Package marker."""'
    assert "sakana" not in init
    collectors = (root / "pipeline" / "pdoom_pipeline" / "collectors" / "__init__.py").read_text(encoding="utf-8")
    assert collectors.strip() == '"""Package marker."""'
    assert "sakana" not in collectors
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/collectors/__init__.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert "sakana_pages" not in text
        assert "catalogs.sakana" not in text
    collect = (root / "pipeline" / "pdoom_pipeline" / "belief" / "collect.py").read_text(encoding="utf-8")
    assert "RssCollector" in collect
