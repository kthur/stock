# GitHub Action Artifact Verifier Skill Reference

Dumped from `d:\Finance\code\stock\.agents\skills\gha-artifact-verifier\SKILL.md`

## Summary
- Verifies prediction artifacts across all strategies for SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ.
- Non-zero data validation and count >= 10 items per market.
- Verification script: `trading_system/scripts/verify_gha_artifacts.py --result-dir trading_system/result --gh-pages-dir gh-pages`.
- GitHub Pages dashboard verification: `gh-pages/index.html` size > 50KB, >= 5 rows per strategy tab panel.
