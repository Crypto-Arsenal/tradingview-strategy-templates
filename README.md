# tradingview-templates

## sync position
- Will sync TV strategy position

## compounding strategy 復利策略
- PPC 是複利策略：就是假設初始 10,000，虧錢情況下都是下當前數量，譬如虧損到 9,000 時，觸發策略就下 9,000。

## reversal strategy 反向開單

- Only need to pass in `openLong` or `openShort`
- Any opened position will be closed before opening anything
