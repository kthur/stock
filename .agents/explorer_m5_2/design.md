# Comprehensive Technical Design: Milestone 5 (R5: LLM/NLP DART & SEC Filing Sentiment Engine)

## 1. System Context & Objectives

Milestone 5 (R5) introduces an institutional-grade **LLM/NLP Filing Sentiment Engine** (`src/core/llm_sentiment_engine.py`) to systematically extract quantitative tone, risk, and catalyst sentiment scores from unstructured corporate disclosures:
- **KRX Market (KOSPI / KOSDAQ / KONEX)**: OpenDART corporate disclosures, quarterly/annual reports ("사업보고서", "분기보고서"), and major management events ("주요경영사항", "자사주", "증자").
- **US Market (SP500 / NASDAQ / RUSSELL2000)**: SEC filings (10-K, 10-Q, 8-K), specifically focusing on high-signal narrative sections such as Management's Discussion and Analysis (MD&A) and Risk Factors.

The sentiment signals produced by `LLMSentimentEngine` dynamically modulate disclosure base weights in **Strategy 10: Event-Driven Momentum Engine** (`src/core/event_driven.py`), transforming qualitative narrative tone into quantitative return multipliers ($0.65\times$ to $1.35\times$) for the 18-strategy dynamic ensemble pipeline.

---

## 2. Core Architecture & Component Specifications

### 2.1 Component Overview

```
                        ┌─────────────────────────────────────────────────────────────┐
                        │              Corporate Filings & Disclosures               │
                        │  (OpenDART API / Local Storage / SEC Electronic Filings)    │
                        └──────────────────────────────┬──────────────────────────────┘
                                                       │ raw filing text / HTML
                                                       ▼
                        ┌─────────────────────────────────────────────────────────────┐
                        │                 LLMSentimentEngine                          │
                        │                                                             │
                        │  1. Text Preprocessing & Cleaning                           │
                        │  2. Key Section Extraction (MD&A / Risk Factors / DART)     │
                        │  3. Dual-Mode Tone Analyzer                                 │
                        │     ├─ Primary: FinBERT / HuggingFace Transformers          │
                        │     └─ Fallback: Loughran-McDonald & Korean Lexicon NLP     │
                        │  4. Score Normalization (Tone Score ∈ [-1.0, +1.0])         │
                        └──────────────────────────────┬──────────────────────────────┘
                                                       │ SentimentScore
                                                       ▼
                        ┌─────────────────────────────────────────────────────────────┐
                        │                 EventDrivenEngine                           │
                        │                                                             │
                        │  Base Event Weight W_base ∈ [0.0, 1.0]                      │
                        │  × Sentiment Multiplier M_sent = (1 + γ * tone * confidence)│
                        │  = Event Catalyst Score ∈ [0.0, 1.0]                        │
                        └──────────────────────────────┬──────────────────────────────┘
                                                       │
                                                       ▼
                        ┌─────────────────────────────────────────────────────────────┐
                        │             18-Strategy Ensemble Pipeline                   │
                        │  (EnsembleScoringEngine / event_driven_predictions.txt)     │
                        └─────────────────────────────────────────────────────────────┘
```

---

### 2.2 Data Classes (`src/core/llm_sentiment_engine.py`)

#### `SentimentScore`
Dataclass capturing full financial sentiment output metrics:

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

@dataclass
class SentimentScore:
    """
    Structured container for financial document sentiment metrics.
    """
    positive: float           # Positive tone probability / ratio [0.0, 1.0]
    negative: float           # Negative tone probability / ratio [0.0, 1.0]
    tone_score: float         # Net financial tone score [-1.0, +1.0]
    confidence: float         # Confidence level of the classification [0.0, 1.0]
    mode_used: str            # Mode used: 'transformer_finbert' or 'dictionary_fallback'
    sections_analyzed: List[str] = field(default_factory=list)  # Sections parsed (e.g. ['MD&A', 'Risk Factors'])
    metadata: Dict[str, Any] = field(default_factory=dict)       # Detailed diagnostics & keyword match counters
```

---

### 2.3 `LLMSentimentEngine` Class Design

```python
class LLMSentimentEngine:
    """
    Institutional Filing Sentiment Engine with dual-mode architecture:
    1. Primary Model: FinBERT / HuggingFace Transformers (FinBERT-Prosus for English, KR-FinBERT-SC for Korean).
    2. Fallback Model: Loughran-McDonald (LM) Financial Lexicon for English & Domain-Specific Korean Financial Dictionary.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        use_gpu: bool = False,
        primary_model_en: str = "ProsusAI/finbert",
        primary_model_kr: str = "snunlp/KR-FinBERT-SC",
        fallback_only: bool = False
    ):
        self.config = config
        self.use_gpu = use_gpu
        self.primary_model_en = primary_model_en
        self.primary_model_kr = primary_model_kr
        self.fallback_only = fallback_only
        self._tokenizer = None
        self._model = None
        self._primary_available = False

        if not self.fallback_only:
            self._init_primary_model()

    def analyze_filing_sentiment(
        self,
        filing_text: str,
        market: str = 'KOSPI',
        section_type: Optional[str] = None
    ) -> SentimentScore:
        """
        Main entry point for analyzing financial filing text.
        Extracts sections, cleans text, evaluates tone via Primary Transformer or Fallback Lexicon,
        and returns normalized SentimentScore (-1.0 to +1.0).
        """
        if not filing_text or not isinstance(filing_text, str) or not filing_text.strip():
            return SentimentScore(
                positive=0.0,
                negative=0.0,
                tone_score=0.0,
                confidence=0.0,
                mode_used='none',
                sections_analyzed=[],
                metadata={'reason': 'empty_input'}
            )

        # Step 1: Preprocess raw text
        cleaned_text = self._preprocess_text(filing_text)

        # Step 2: Key Section Extraction
        extracted_sections = self.extract_key_sections(cleaned_text, market=market)
        target_text = " ".join(extracted_sections.values()) if extracted_sections else cleaned_text
        sections_analyzed = list(extracted_sections.keys()) if extracted_sections else ['FULL_TEXT']

        # Step 3: Dual-Mode Execution (Primary Transformer with Fallback fallback)
        if self._primary_available and not self.fallback_only:
            score = self._analyze_primary_transformer(target_text, market=market)
            if score is not None:
                score.sections_analyzed = sections_analyzed
                return score

        # Fallback Mode: Loughran-McDonald & Korean Lexicon
        score = self._analyze_fallback_lexicon(target_text, market=market)
        score.sections_analyzed = sections_analyzed
        return score
```

---

## 3. Text Preprocessing & Section Extraction

### 3.1 Preprocessing Pipeline (`_preprocess_text`)
Raw SEC (EDGAR HTML) and DART (XML/HTML) filings contain tags, table borders, entities, and line breaks.

```python
def _preprocess_text(self, raw_text: str) -> str:
    # 1. Strip HTML/XML tags
    clean = re.sub(r'<[^>]+>', ' ', raw_text)
    # 2. Decode HTML entities (&amp;, &lt;, &gt;, &nbsp;)
    clean = html.unescape(clean)
    # 3. Remove non-printable / control characters while retaining Korean Unicode & ASCII
    clean = re.sub(r'[\r\t\f\v]+', ' ', clean)
    # 4. Collapse multiple spaces & blank lines
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean
```

### 3.2 Key Section Extractor (`extract_key_sections`)
High-signal narrative sections are extracted using regex pattern matching:

- **US Filings (SEC 10-K / 10-Q / 8-K)**:
  - `Item 1A`: Risk Factors (`Item\s+1A[\.\s:\-]+Risk\s+Factors`)
  - `Item 7`: Management's Discussion and Analysis (`Item\s+7[\.\s:\-]+Management['’]s\s+Discussion`)
  - `Item 2`: Financial Statements & Management Analysis (`Item\s+2[\.\s:\-]+Management['’]s\s+Discussion`)

- **KRX Filings (OpenDART 사업/반기/분기보고서 & 주요경영사항)**:
  - `MD&A`: `이사회의\s*경영진단\s*및\s*분석의견` / `경영진단\s*의견`
  - `Business Summary`: `사업의\s*내용` / `주요\s*제품\s*및\s*서비스`
  - `Financial Status`: `재무에\s*관한\s*사항` / `요약재무정보`
  - `Major Disclosures`: `주요경영사항` / `자기주식` / `증자`

```python
def extract_key_sections(self, filing_text: str, market: str = 'KOSPI') -> Dict[str, str]:
    sections = {}
    mkt = str(market).strip().upper()

    if mkt in ('SP500', 'NASDAQ', 'RUSSELL2000', 'US'):
        # SEC Patterns
        mda_match = re.search(r'(Item\s+7[\.\s:\-]+Management.*?)(?=Item\s+7A|Item\s+8|$)', filing_text, re.IGNORECASE | re.DOTALL)
        if mda_match:
            sections['Item_7_MDA'] = mda_match.group(1)[:10000]
        
        rf_match = re.search(r'(Item\s+1A[\.\s:\-]+Risk\s+Factors.*?)(?=Item\s+1B|Item\s+2|$)', filing_text, re.IGNORECASE | re.DOTALL)
        if rf_match:
            sections['Item_1A_Risk_Factors'] = rf_match.group(1)[:10000]
    else:
        # DART Patterns
        mda_match = re.search(r'(이사회의\s*경영진단\s*및\s*분석의견.*?)(?=IV\.|V\.|사업의|재무에|$)', filing_text, re.DOTALL)
        if mda_match:
            sections['DART_MDA'] = mda_match.group(1)[:10000]
            
        biz_match = re.search(r'(사업의\s*내용.*?)(?=III\.|IV\.|재무에|$)', filing_text, re.DOTALL)
        if biz_match:
            sections['DART_Business'] = biz_match.group(1)[:10000]

    return sections
```

---

## 4. Dual-Mode Tone Analyzer Specification

### 4.1 Primary Mode: FinBERT / Transformer Architecture (`_analyze_primary_transformer`)

1. **Model Selection**:
   - English Market (`SP500`): `ProsusAI/finbert` (outputs: positive, negative, neutral).
   - Korean Market (`KOSPI`/`KOSDAQ`): `snunlp/KR-FinBERT-SC` (outputs: positive, negative, neutral).
2. **512 Token Window Chunking**:
   - Text is split into sliding window chunks of max 512 tokens.
   - For each chunk $i$, retrieve probabilities $P_i(pos), P_i(neg), P_i(neu)$.
3. **Probability Aggregation**:
   $$P_{pos} = \frac{1}{N}\sum_{i=1}^N P_i(pos), \quad P_{neg} = \frac{1}{N}\sum_{i=1}^N P_i(neg)$$
   $$\text{tone\_score} = P_{pos} - P_{neg} \in [-1.0, +1.0]$$
   $$\text{confidence} = \max(P_{pos}, P_{neg}) + 0.5 \times (1.0 - P_{neu})$$

If `transformers` or `torch` is not installed or model weights cannot be downloaded (offline environment), the engine safely catches `ImportError` / `Exception` and seamlessly delegates to Fallback mode.

---

### 4.2 Fallback Mode: Loughran-McDonald & Korean Lexicon NLP (`_analyze_fallback_lexicon`)

#### A. English Filings: Loughran-McDonald (LM) Financial Dictionary
Loughran & McDonald (2011) demonstrate that general sentiment dictionaries (like Harvard GI) misclassify standard accounting terms (e.g. "cost", "liability", "depreciation") as negative. LM lexicon contains finance-specific wordlists:

- **LM Positive Terms** ($W_{pos}$): `outperform`, `profitability`, `synergy`, `exceed`, `rebound`, `efficiency`, `innovation`, `robust`, `strong`, `gain`, `accretive`, `dividend`, `upside`.
- **LM Negative Terms** ($W_{neg}$): `impairment`, `restructuring`, `litigation`, `default`, `bankruptcy`, `adverse`, `breach`, `penalty`, `headwind`, `downgrade`, `delisting`, `deficit`, `loss`, `write-down`, `dilution`.
- **LM Uncertainty / Litigious Terms**: `uncertainty`, `contingent`, `pending`, `lawsuit`, `investigation`, `subpoena`.

#### B. Korean Filings: DART Korean Financial Dictionary & Regex Matches
- **Bullish Disclosures & Keywords** ($K_{pos}$):
  - `무상증자` (Bonus issue / Free share distribution): +0.90
  - `자기주식 소각` / `자사주 소각` (Share cancellation): +0.85
  - `자기주식 취득` / `자사주 매입` (Share buyback): +0.75
  - `영업이익 흑자전환` / `영업이익 증가` (Profit turn/growth): +0.80
  - `최대실적` / `사상 최대` (Record earnings): +0.80
  - `수주계약` / `단일판매계약` (Major contract): +0.70
- **Bearish Disclosures & Keywords** ($K_{neg}$):
  - `유상증자` (Dilutive rights offering): -0.75
  - `자기주식 처분` / `자사주 매각` (Share disposal/supply pressure): -0.70
  - `전환사채` / `CB발행` / `BW발행` (Convertible bond overhang): -0.65
  - `영업손실` / `적자전환` (Operating loss / Loss turn): -0.80
  - `횡령` / `배임` (Embezzlement / Breach of trust): -0.95
  - `관리종목` / `회생절차` / `파산` (Watchlist / Insolvency): -0.95
  - `감자` / `자본금 감축` (Capital reduction): -0.85

#### Formula for Fallback Score Normalization:
$$\text{pos\_score} = \sum_{w \in W_{pos}} \text{count}(w) \cdot \text{weight}(w)$$
$$\text{neg\_score} = \sum_{w \in W_{neg}} \text{count}(w) \cdot \text{weight}(w)$$
$$\text{raw\_tone} = \frac{\text{pos\_score} - \text{neg\_score}}{\text{pos\_score} + \text{neg\_score} + \epsilon}$$
$$\text{tone\_score} = \text{clip}(\text{raw\_tone}, -1.0, +1.0)$$
$$\text{confidence} = \min\left(1.0, \frac{\text{pos\_score} + \text{neg\_score}}{15.0}\right)$$

---

## 5. EventDrivenEngine Integration Design

`EventDrivenEngine` (`trading_system/src/core/event_driven.py`) is updated to incorporate sentiment score metrics into catalyst scores.

### 5.1 Modified Method Signature & Logic

```python
class EventDrivenEngine:
    ...
    def calculate_event_score(
        self,
        filing_item: Dict[str, Any],
        sentiment_score: Optional[SentimentScore] = None
    ) -> float:
        """
        Calculates sentiment-adjusted event score for a corporate disclosure item.
        """
        pblntf_ty = filing_item.get('pblntf_ty', '')
        report_nm = filing_item.get('report_nm', '')
        
        # 1. Determine Base Weight
        base_weight = self.EVENT_WEIGHTS.get(pblntf_ty, 0.50)
        
        # 2. Text Keyword Adjustment
        if '유상증자' in report_nm or '전환사채' in report_nm:
            base_weight = 0.20
        elif '자기주식' in report_nm or '자사주' in report_nm:
            if '처분' in report_nm or '매각' in report_nm:
                base_weight = 0.20
            elif '취득' in report_nm or '소각' in report_nm:
                base_weight = 0.85
        elif '무상증자' in report_nm or '주식분할' in report_nm:
            base_weight = 0.90

        # 3. Apply Sentiment Multiplier if SentimentScore provided
        if sentiment_score is not None:
            # gamma = 0.35 -> Multiplier range: [0.65x, 1.35x]
            gamma = 0.35
            multiplier = 1.0 + gamma * sentiment_score.tone_score * sentiment_score.confidence
            adjusted_score = base_weight * multiplier
            return float(np.clip(adjusted_score, 0.0, 1.0))

        return float(base_weight)
```

---

## 6. Pipeline Integration (`run_pipeline.py`)

In `trading_system/run_pipeline.py` (Step 10g: Strategy 10 Event-Driven Momentum Engine):

```python
    # 10g. Strategy 10: Event-Driven Momentum Engine & Filing Sentiment Integration
    try:
        from src.core.event_driven import EventDrivenEngine
        from src.core.llm_sentiment_engine import LLMSentimentEngine
        
        logger.info("Computing Strategy 10: Event-Driven Momentum & Filing Sentiment Scores...")
        sentiment_engine = LLMSentimentEngine(config=cfg)
        event_engine = EventDrivenEngine(dart_api_key=getattr(cfg, 'dart_api_key', ''))
        
        # Analyze active disclosures & symbols
        event_df = event_engine.compute_event_scores(
            symbols=list(infer_data_dict.keys()),
            prices_dict=infer_data_dict
        )
        ...
```

The prediction output report (`event_driven_predictions.txt`) will log the sentiment tone score, positive/negative probability, and mode used (`transformer_finbert` vs `dictionary_fallback`).

---

## 7. Unit Test Specification (`tests/test_llm_sentiment_engine.py`)

The test suite validates both online transformer capability and offline dictionary execution, section extraction, edge cases, and `EventDrivenEngine` integration:

1. **`test_engine_initialization`**: Verify engine initializes in default and fallback modes.
2. **`test_text_preprocessing`**: Test HTML/XML tag removal, entity decoding, and space normalization.
3. **`test_sec_section_extraction`**: Test extraction of Item 1A (Risk Factors) and Item 7 (MD&A) from synthetic SEC 10-K filings.
4. **`test_dart_section_extraction`**: Test extraction of "사업의 내용" and "이사회의 경영진단" from DART report text.
5. **`test_loughran_mcdonald_english_lexicon`**: Verify English text with strong positive earnings language yields `tone_score > 0.4`, and litigation/impairment text yields `tone_score < -0.4`.
6. **`test_korean_financial_lexicon`**: Verify Korean DART text with `무상증자`/`자사주 소각` yields `tone_score > 0.5`, while `유상증자`/`횡령` yields `tone_score < -0.5`.
7. **`test_score_normalization_and_bounds`**: Verify $ positive, negative \in [0.0, 1.0] $, $ tone\_score \in [-1.0, +1.0] $, $ confidence \in [0.0, 1.0] $.
8. **`test_primary_transformer_mock`**: Test transformer primary analyzer using mock pipelines to ensure probability aggregation and token chunking work properly.
9. **`test_event_driven_engine_integration`**: Test `EventDrivenEngine.calculate_event_score` with positive, negative, and neutral sentiment inputs to confirm multiplier scaling ($0.65\times$ to $1.35\times$).
10. **`test_edge_cases_and_robustness`**: Test empty strings, None, non-ASCII Unicode characters, huge 1MB documents, unknown markets.

---

## 8. Verification & Test Plan

1. **Run Unit Test Suite**:
   ```bash
   .venv/bin/pytest tests/test_llm_sentiment_engine.py -v
   ```
2. **Run Comprehensive Pipeline Test**:
   ```bash
   .venv/bin/pytest tests/ -v
   ```
3. **Verify File Layout Compliance**:
   - `trading_system/src/core/llm_sentiment_engine.py` (Implementation)
   - `src/core/llm_sentiment_engine.py` (Root forwarder)
   - `tests/test_llm_sentiment_engine.py` (Pytest file)
