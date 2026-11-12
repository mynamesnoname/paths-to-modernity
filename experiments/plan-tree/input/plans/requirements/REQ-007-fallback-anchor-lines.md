# REQ-007 — Allow fallback systemic-redshift anchors

Decision owner: project user, 2026-10-12.

Raw request: “把它们从list里放出来吧，如果一个 QSO 只确证了 Lyα、C IV、C III] 这三条谱线，又不能用它们定标，岂不是没有anchor了？不如把它们也按电离度放进anchor表里。”

## Interpretation and scientific boundary

- Retire the blanket `excluded_from_anchor` veto for currently listed lines. A credible line may anchor a redshift when no better, observable candidate exists; the result must state when that anchor is only a biased systemic-redshift proxy.
- Extend the existing anchor ranking with lower-priority ultraviolet lines. Rank the non-resonant candidates approximately by increasing ionization, but place resonant Lyα last because its profile is affected by absorption; ionization energy alone does not represent systemic-redshift accuracy.
- Na D components may anchor only as independently credible, resolved lines; avoid double-counting them alongside the blended Na D label.
- Preserve line identity checks, fit quality, masks, blend caveats and Unknown/null abstention when no line is credible. This request does not approve a numeric velocity correction or guarantee of systemic accuracy.

References: Hewett & Wild (2010), https://academic.oup.com/mnras/article/405/4/2302/1045471 ; Mason et al. (2017), https://academic.oup.com/mnras/article/469/4/4675/3798771 ; SDSS spectroscopic redshift algorithm, https://classic.sdss.org/dr3/algorithms/redshift_type.php .
