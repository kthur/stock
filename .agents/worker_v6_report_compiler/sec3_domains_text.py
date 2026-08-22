# -*- coding: utf-8 -*-
import re
from pathlib import Path

def get_sec3_text():
    root = Path('.').resolve()
    d1 = (root / '.agents/explorer_d1_aiml/analysis.md').read_text(encoding='utf-8').splitlines()
    d2 = (root / '.agents/explorer_d2_port_risk/analysis.md').read_text(encoding='utf-8').splitlines()
    d3 = (root / '.agents/explorer_d3_strategies/analysis.md').read_text(encoding='utf-8').splitlines()
    d4 = (root / '.agents/explorer_d4_oms_cost/analysis.md').read_text(encoding='utf-8').splitlines()
    d5 = (root / '.agents/explorer_d5_pipeline_infra/analysis.md').read_text(encoding='utf-8').splitlines()

    chunks = []
    chunks.append('---\n')
    chunks.append('## 3. ë„ë©”ì¸ë³„ ì„¸ë¶€ ì¹´ë„¤ì¤ ë¹ ìˆ˜ì •ì•ˆ (Deep-Dive Analysis & Remediations)\n')

    # 3.1 Domain 1
    chunks.append('### 3.1 Domain 1: AI/ML & ì…ªÞw²vðƒ®²ÓªÊÃ²Ä€¡XØ´ÀÄøXØ´Àà¥q¸œ¤(€€€¡Õ¹­Ì¹…ÁÁ•¹ q¸œ™©½¥¸¡ÅlÐäèÔÐÍt¤€¬€q¸œ¤((€€€€Œ€Ì¸È½µ…¥¸€È(€€€¡Õ¹­Ì¹…ÁÁ•¹ q¸´´µq¹q¸œ¤(€€€¡Õ¹­Ì¹…ÁÁ•¹ œŒŒŒ€Ì¸È½µ…¥¸€Èèƒ¶>³¶*ã¶>Ó®šó²jP€˜ƒ²«yÙ¥fØÚÂ«;^ÙY’…cbÓ’âcbÓb•Æâr¢6‡Væ·2æVæB‚uÆârf¦ö–â†C%³CS£CS5Ò’²uÆâr ¢22ã2FöÖ–â0¢6‡Væ·2æVæB‚uÆâÒÒÕÆåÆâr¢6‡Væ·2æVæB‚r2222ã2FöÖ–â3¢3¸ÈÉÈNºËBÊN¹ê’ÙYNÊxBb¸ÛÉÛNØK88ŽÉÛNÉkB…cbÓrâcbÓ#B•Æâr¢6‡Væ·2æVæB‚uÆârf¦ö–â†C5³33¥Ò’²uÆâr ¢22ãBFöÖ–â@¢6‡Væ·2æVæB‚uÆâÒÒÕÆåÆâr¢6‡Væ·2æVæB‚r2222ãBFöÖ–âC¢ÈºNÙ[’ôÕ2b«¹éŽ»˜NÉª’…cbÓ#RâcbÓ3•Æâr¢6‡Væ·2æVæB‚uÆâræ¦ö–â†CE³3“£CSuÒ’²uÆâr ¢22ãRFöÖ–âP¢6‡Væ·2æVæB‚uÆâÒÒÕÆåÆâr¢6‡Væ·2æVæB‚u2222ãRFöÖ–âS¢ØÈÎÉÛNÙHN¹ÛÎÉÛÂÂ4’ô4BbÈZ­çU‡¶§¶²Â €¡XØ´ÌÈøXØ´ÌÔ¥q¸œ¤(€€€Õ}ÑáÐ€ô€q¸œ™©½¥¸¡ÕlÍ èÌÐÅt¤(€€€Õ}ÑáÐ€ôÕ}ÑáÐ¹É•Á±…” œŒŒŒØØ´Èäœ°€œŒŒŒŒXØ´ÌÈœ¤¹‰•Á±…” œŒŒŒXØ´Èäœ°€œŒŒŒXØ´ÌÈœ¤(€€€Õ}ÑáÐ€ôÕ}ÑáÐ¹É•Á±…” œŒŒŒŒØØ´ÌÀœ°€œŒŒŒŒXØ´ÌÌœ¤¹‰•Á±…” œŒŒŒXØ´ÌÀœ°€œŒŒŒXØ´ÌÌœ¤(€€€Õ}ÑáÐ€ôÕ}ÑáÐ¹É•Á±…” œŒŒŒŒØØ´ÌÄœ°€œŒŒŒŒXØ´ÌÐœ¤¹‰•Á±…” œŒŒŒXØ´ÌÄœ°€œŒŒŒXØ´ÌÐœ¤(€€€Õ}ÑáÐ€ôÕ}ÑáÐ¹É•Á±…” œŒŒŒŒØØ´ÌÈœ°€œŒŒŒŒXØ´ÌÔœ¤¹‰•Á±…” œŒŒŒXØ´ÌÈœ°€œŒŒŒXØ´ÌÔœ¤(€€€¡Õ¹­Ì¹…ÁÁ•¹¡Õ}ÑáÐ€¬€q¸œ¤((€€€É•ÑÕÉ¸€q¸œ™©½¥¸¡¡Õ¹­Ì¤(