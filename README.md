# tradingview-templates

## Sync position side
如果你的策略是全倉所以他會去同步你 TＶ 策略傳來的倉位方向 
---
像是  TV 傳 long 我們就會開多 100% 
在傳 flat 我們就會平倉
在傳 short 我們就會開空 100%

## sync position
- Will sync TV strategy position

## compounding strategy 單利策略
- PPC 是複利策略：就是假設初始 10,000，虧錢情況下都是下當前數量，譬如虧損到 9,000 時，觸發策略就下 9,000。

## reversal strategy 反向開單

- Only need to pass in `openLong` or `openShort`
- Any opened position will be closed before opening anything
