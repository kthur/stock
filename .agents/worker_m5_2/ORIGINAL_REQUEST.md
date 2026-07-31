## 2026-07-31T14:41:12Z

Remediate the Language Detection Heuristic Bug in `trading_system/src/core/llm_sentiment_engine.py` identified by `challenger_m5_1`:

Bug Details:
1. In `trading_system/src/core/llm_sentiment_engine.py` (line 157):
   `is_english = market in ["SP500", "NASDAQ", "RUSSELL2000"] or any(ord(c) < 128 for c in text[:50] if c.isalpha())`
2. Korean DART disclosures (`market="KOSPI"` or `"KOSDAQ"`) starting with English system headers or metadata (e.g. `"DART Official Filing Report for Stock Symbol 005930. 당사는 영업이익증가..."`) cause `any(ord(c) < 128 for c in text[:50] if c.isalpha())` to evaluate to `True`.
3. This incorrectly switches the parser to English Loughran-McDonald lexicon, missing Korean DART terms (`POS_TERMS_KR` / `NEG_TERMS_KR`) and producing false neutral scores (0.50).

Remediation Instructions:
1. Inspect `trading_system/src/core/llm_sentiment_engine.py`.
2. Update language detection logic to check for Hangul characters:
   ```python
   has_hangul = any('\uac00' <= c <= '\ud7a3' for c in text)
   if market in ["KOSPI", "KOSDAQ", "KONEX"] or has_hangul:
       # Process with Korean DART lexicon parser
   ```
3. Update unit tests in `trading_system/tests/test_llm_sentiment_engine.py` and `tests/test_llm_sentiment_engine.py`:
   - Add explicit test case with English header prepended to Korean DART disclosure text (e.g. `"DART Filing 005930: 당사는 흑자전환 및 영업이익증가..."`), asserting that Korean DART terms are matched and positive sentiment score > 0.50 is returned.
4. Run unit tests: `.venv\Scripts\python.exe -m pytest trading_system/tests/test_llm_sentiment_engine.py tests/test_llm_sentiment_engine.py -v`.
5. Run full regression test suite: `.venv\Scripts\python.exe -m pytest tests/ -v`.

Write your report to `d:\Finance\code\stock\.agents\worker_m5_2\handoff.md` and notify orchestrator when done via `send_message`.
