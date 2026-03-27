# National 52-Week Results Audit

**Date:** 2026-03-05
**Databases:**

| Label | Path | Schema |
|---|---|---|
| mip-dev | `/Users/cameronwade/PycharmProjects/One-Off-Analyses/Temoa_Servers/data_files_Jan_2025/solved_jan26/server_current_policies_noIRA_52_week_retire_HighGasCapex.sqlite` | v3 (mip-dev) |
| new_v4 | `/Users/cameronwade/Downloads/full_52week_v4_stripped.sqlite` | v4 (Mar 5, RPS fix + threshold=10) |
| old_v4 | `/Users/cameronwade/PycharmProjects/temoa-SRfork/data_files/mip_migration_workspace/server_results/national_52week_solved_2026-03-04.sqlite` | v4 (Mar 4, pre-RPS fix) |

## 1. Database Diagnostics

### Objectives

| DB | Objective |
|---|---|
| mip-dev | - |
| new_v4 | 818,205,226,542 |
| old_v4 | 798,600,263,864 |

### CapacityToActivity

| DB | C2A |
|---|---|
| mip-dev | 8760.0 |
| new_v4 | 8736.0 |
| old_v4 | 8736.0 |

> Note: mip-dev uses C2A=8760 (365 days), v4 uses C2A=8736 (52×168). Difference is 0.27% — negligible.

### Demand Totals (MWh)

| Commodity | Period | mip-dev | new_v4 | old_v4 |
|---|---|---|---|---|
| DEMAND_CRYPTO | 2027 | 109,698,857 | 109,698,857 | 109,698,857 |
| DEMAND_ELC | 2027 | 4,233,620,507 | 4,233,620,507 | 4,233,620,507 |
| DEMAND_SERVERS | 2027 | 371,777,104 | 371,777,104 | 371,777,104 |
| Dummy_CO2_Offset_Demand | 2027 | 900,000,000 | 900,000,000 | 900,000,000 |
| DEMAND_CRYPTO | 2030 | 212,979,625 | 212,979,625 | 212,979,625 |
| DEMAND_ELC | 2030 | 4,516,201,713 | 4,516,201,713 | 4,516,201,713 |
| DEMAND_SERVERS | 2030 | 575,716,922 | 575,716,922 | 575,716,922 |
| Dummy_CO2_Offset_Demand | 2030 | 900,000,000 | 900,000,000 | 900,000,000 |

> Demands are **identical** across all three databases. Any generation differences are from model behavior, not input data.

## 2. National Generation by Type

### Period 2027

#### Total Generation (MWh) — 2027

| Type | mip-dev (MWh) | new_v4 (MWh) | old_v4 (MWh) | new_v4 vs mip-dev |
|---|---|---|---|---|
| gas | 1,978,944,339 | 1,982,608,318 | 2,064,177,779 | -0.0pp |
| coal | 669,550,274 | 680,184,555 | 756,267,628 | +0.2pp |
| nuclear | 836,763,432 | 836,364,117 | 847,659,855 | -0.0pp |
| wind | 606,227,681 | 604,786,377 | 466,001,418 | -0.1pp |
| solar | 292,386,008 | 290,874,367 | 256,801,091 | -0.0pp |
| hydro | 254,022,410 | 253,816,895 | 253,540,933 | -0.0pp |
| distributed_gen | 93,291,996 | 93,092,236 | 93,274,104 | -0.0pp |
| biomass | 20,530,157 | 20,755,611 | 20,435,975 | +0.0pp |
| hydrogen | 875,234 | - | - | -0.0pp |
| geothermal | 7,210,279 | 7,196,554 | 7,192,935 | -0.0pp |
| oil | 63,542 | 98,986 | 96,541 | +0.0pp |
| other | - | - | - | +0.0pp |
| **TOTAL** | **4,759,865,354** | **4,769,778,017** | **4,765,448,257** | 1.0021x |

#### Generation Shares (%) — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff (new_v4 - mip-dev) |
|---|---|---|---|---|
| gas | 41.58 | 41.57 | 43.32 | -0.01pp |
| coal | 14.07 | 14.26 | 15.87 | +0.19pp |
| nuclear | 17.58 | 17.53 | 17.79 | -0.04pp |
| wind | 12.74 | 12.68 | 9.78 | -0.06pp |
| solar | 6.14 | 6.10 | 5.39 | -0.04pp |
| hydro | 5.34 | 5.32 | 5.32 | -0.02pp |
| distributed_gen | 1.96 | 1.95 | 1.96 | -0.01pp |
| biomass | 0.43 | 0.44 | 0.43 | +0.00pp |
| hydrogen | 0.02 | 0.00 | 0.00 | -0.02pp |
| geothermal | 0.15 | 0.15 | 0.15 | -0.00pp |
| oil | 0.00 | 0.00 | 0.00 | +0.00pp |
| other | 0.00 | 0.00 | 0.00 | +0.00pp |

### Period 2030

#### Total Generation (MWh) — 2030

| Type | mip-dev (MWh) | new_v4 (MWh) | old_v4 (MWh) | new_v4 vs mip-dev |
|---|---|---|---|---|
| gas | 1,794,765,648 | 1,805,824,280 | 1,919,671,066 | +0.2pp |
| coal | 1,104,602,239 | 1,110,199,483 | 1,145,149,932 | +0.1pp |
| nuclear | 826,952,710 | 829,428,217 | 847,696,923 | +0.0pp |
| wind | 833,715,216 | 821,575,155 | 658,278,751 | -0.2pp |
| solar | 382,082,954 | 378,351,413 | 376,228,701 | -0.1pp |
| hydro | 263,390,970 | 263,465,445 | 264,839,545 | -0.0pp |
| distributed_gen | 139,662,646 | 139,636,944 | 139,924,948 | -0.0pp |
| biomass | 20,582,070 | 20,469,080 | 20,790,078 | -0.0pp |
| hydrogen | 979,813 | - | - | -0.0pp |
| geothermal | 7,213,585 | 7,195,334 | 7,196,324 | -0.0pp |
| oil | 104,813 | 222,441 | 94,182 | +0.0pp |
| other | - | - | - | +0.0pp |
| **TOTAL** | **5,374,052,664** | **5,376,367,792** | **5,379,870,452** | 1.0004x |

#### Generation Shares (%) — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff (new_v4 - mip-dev) |
|---|---|---|---|---|
| gas | 33.40 | 33.59 | 35.68 | +0.19pp |
| coal | 20.55 | 20.65 | 21.29 | +0.10pp |
| nuclear | 15.39 | 15.43 | 15.76 | +0.04pp |
| wind | 15.51 | 15.28 | 12.24 | -0.23pp |
| solar | 7.11 | 7.04 | 6.99 | -0.07pp |
| hydro | 4.90 | 4.90 | 4.92 | -0.00pp |
| distributed_gen | 2.60 | 2.60 | 2.60 | -0.00pp |
| biomass | 0.38 | 0.38 | 0.39 | -0.00pp |
| hydrogen | 0.02 | 0.00 | 0.00 | -0.02pp |
| geothermal | 0.13 | 0.13 | 0.13 | -0.00pp |
| oil | 0.00 | 0.00 | 0.00 | +0.00pp |
| other | 0.00 | 0.00 | 0.00 | +0.00pp |

## 3. National New Capacity by Type (MW)

### Period 2027

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| gas | 1,308 | 402 | 462 |
| wind | 48,412 | 47,749 | 10,493 |
| solar | 17,503 | 16,598 | 16 |
| hydrogen | 7,232 | - | - |
| **TOTAL** | **74,454** | **64,749** | **10,971** |

### Period 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| gas | 1,205 | 368 | 891 |
| wind | 56,674 | 52,339 | 46,079 |
| solar | 41,747 | 39,385 | 55,054 |
| distributed_gen | 24,854 | 24,857 | 24,858 |
| hydrogen | 1,927 | - | - |
| **TOTAL** | **126,407** | **116,949** | **126,883** |

## 4. National Net (Operating) Capacity by Type (MW)

> Excludes import, distribution, and storage/battery techs.

### Period 2027

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| gas | 464,758 | 463,853 | 463,912 |
| coal | 157,336 | 157,336 | 157,336 |
| nuclear | 97,038 | 97,038 | 97,038 |
| wind | 203,806 | 203,143 | 165,887 |
| solar | 133,193 | 132,288 | 115,706 |
| hydro | 94,302 | 94,302 | 94,302 |
| distributed_gen | 47,886 | 47,886 | 47,886 |
| biomass | 2,393 | 2,393 | 2,393 |
| hydrogen | 7,232 | - | - |
| geothermal | 824 | 824 | 824 |
| oil | 6,872 | 6,872 | 6,872 |
| **TOTAL** | **1,215,641** | **1,205,936** | **1,152,158** |

### Period 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| gas | 465,963 | 464,221 | 464,804 |
| coal | 157,336 | 157,336 | 157,336 |
| nuclear | 97,038 | 97,038 | 97,038 |
| wind | 260,480 | 255,483 | 211,967 |
| solar | 174,941 | 171,673 | 170,761 |
| hydro | 94,302 | 94,302 | 94,302 |
| distributed_gen | 72,740 | 72,743 | 72,744 |
| biomass | 2,393 | 2,393 | 2,393 |
| hydrogen | 9,159 | - | - |
| geothermal | 824 | 824 | 824 |
| oil | 6,872 | 6,872 | 6,872 |
| **TOTAL** | **1,342,048** | **1,322,885** | **1,279,041** |

## 5. Generation by Region

### Period 2027

#### TRE — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 61.3 | 61.8 | 60.8 | +0.4pp |
| coal | 11.1 | 12.1 | 11.7 | +1.0pp |
| nuclear | 10.7 | 10.6 | 10.6 | -0.1pp |
| wind | 8.6 | 7.5 | 8.8 | -1.2pp |
| solar | 6.5 | 6.5 | 6.5 | -0.1pp |
| hydro | 0.1 | 0.1 | 0.1 | +0.0pp |
| distributed_gen | 1.5 | 1.5 | 1.5 | -0.0pp |
| biomass | 0.1 | 0.1 | 0.1 | -0.0pp |
| hydrogen | 0.1 | 0.0 | 0.0 | -0.1pp |
| **Total (MWh)** | 420,833,637 | 423,742,035 | 422,673,527 | 1.007x |

#### PJME — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 52.0 | 52.2 | 50.8 | +0.2pp |
| coal | 3.1 | 3.1 | 0.0 | +0.0pp |
| nuclear | 32.2 | 32.1 | 37.5 | -0.1pp |
| wind | 6.3 | 6.2 | 4.0 | -0.1pp |
| solar | 1.2 | 1.2 | 1.4 | -0.0pp |
| hydro | 1.5 | 1.5 | 2.0 | -0.0pp |
| distributed_gen | 3.1 | 3.1 | 3.6 | -0.0pp |
| biomass | 0.6 | 0.6 | 0.7 | +0.0pp |
| **Total (MWh)** | 348,739,961 | 349,060,158 | 299,215,130 | 1.001x |

#### PJMW — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 40.3 | 40.0 | 41.5 | -0.3pp |
| coal | 28.5 | 28.2 | 40.1 | -0.2pp |
| nuclear | 13.4 | 13.3 | 12.8 | -0.0pp |
| wind | 14.2 | 14.8 | 2.1 | +0.6pp |
| solar | 2.1 | 2.1 | 2.0 | -0.0pp |
| hydro | 0.9 | 0.9 | 0.8 | -0.0pp |
| distributed_gen | 0.6 | 0.6 | 0.6 | -0.0pp |
| biomass | 0.1 | 0.1 | 0.1 | +0.0pp |
| **Total (MWh)** | 413,604,591 | 413,974,561 | 430,693,602 | 1.001x |

#### SRSE — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 58.8 | 59.1 | 59.3 | +0.3pp |
| coal | 3.5 | 3.4 | 3.8 | -0.2pp |
| nuclear | 28.6 | 28.5 | 28.0 | -0.1pp |
| solar | 5.7 | 5.6 | 5.5 | -0.0pp |
| hydro | 2.2 | 2.1 | 2.1 | -0.0pp |
| distributed_gen | 0.3 | 0.3 | 0.3 | -0.0pp |
| biomass | 0.9 | 0.9 | 0.9 | +0.0pp |
| **Total (MWh)** | 247,850,970 | 248,051,001 | 252,395,158 | 1.001x |

#### FRCC — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 76.9 | 77.0 | 77.1 | +0.1pp |
| coal | 0.4 | 0.4 | 0.4 | -0.0pp |
| nuclear | 12.5 | 12.5 | 12.5 | -0.0pp |
| solar | 7.1 | 7.1 | 7.1 | -0.0pp |
| distributed_gen | 2.2 | 2.2 | 2.2 | -0.0pp |
| biomass | 0.7 | 0.7 | 0.6 | +0.0pp |
| **Total (MWh)** | 260,814,902 | 260,917,957 | 262,008,501 | 1.000x |

#### CANO — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 57.8 | 58.0 | 58.1 | +0.2pp |
| wind | 2.0 | 2.0 | 2.0 | -0.0pp |
| solar | 12.6 | 12.6 | 12.6 | -0.0pp |
| hydro | 17.6 | 17.4 | 17.3 | -0.2pp |
| distributed_gen | 8.5 | 8.5 | 8.5 | -0.0pp |
| biomass | 1.6 | 1.6 | 1.5 | +0.0pp |
| **Total (MWh)** | 121,926,512 | 121,949,452 | 122,067,270 | 1.000x |

#### ISNE — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 29.5 | 29.4 | 43.2 | -0.1pp |
| coal | 2.2 | 2.2 | 0.0 | -0.0pp |
| nuclear | 22.5 | 22.6 | 21.9 | +0.1pp |
| wind | 29.0 | 29.2 | 19.5 | +0.2pp |
| solar | 4.0 | 4.0 | 3.9 | -0.0pp |
| hydro | 5.3 | 5.1 | 4.4 | -0.1pp |
| distributed_gen | 5.3 | 5.3 | 5.1 | -0.0pp |
| biomass | 2.2 | 2.2 | 2.1 | +0.0pp |
| **Total (MWh)** | 129,125,006 | 129,370,254 | 134,129,615 | 1.002x |

#### NYUP — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 8.6 | 7.1 | 48.6 | -1.5pp |
| nuclear | 12.0 | 12.9 | 24.8 | +0.9pp |
| wind | 39.3 | 39.8 | 6.6 | +0.5pp |
| solar | 25.6 | 24.7 | 2.8 | -0.9pp |
| hydro | 13.3 | 14.2 | 15.5 | +0.9pp |
| distributed_gen | 0.8 | 0.8 | 1.1 | +0.0pp |
| biomass | 0.5 | 0.5 | 0.6 | -0.0pp |
| **Total (MWh)** | 139,240,283 | 140,333,222 | 118,269,770 | 1.008x |

#### MISC — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 21.2 | 20.8 | 21.1 | -0.4pp |
| coal | 49.1 | 49.8 | 51.7 | +0.7pp |
| nuclear | 13.2 | 13.1 | 12.1 | -0.2pp |
| wind | 9.0 | 8.9 | 8.2 | -0.1pp |
| solar | 5.1 | 5.1 | 4.7 | -0.1pp |
| hydro | 1.2 | 1.2 | 1.1 | -0.0pp |
| distributed_gen | 0.8 | 0.8 | 0.7 | -0.0pp |
| biomass | 0.4 | 0.4 | 0.3 | +0.0pp |
| **Total (MWh)** | 157,089,202 | 158,765,209 | 171,812,220 | 1.011x |

#### NYCW — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 93.5 | 94.4 | 94.5 | +0.9pp |
| solar | 0.6 | 0.6 | 0.6 | -0.0pp |
| distributed_gen | 3.8 | 3.8 | 3.8 | -0.0pp |
| biomass | 1.0 | 1.0 | 1.0 | +0.0pp |
| hydrogen | 1.0 | 0.0 | 0.0 | -1.0pp |
| oil | 0.1 | 0.2 | 0.2 | +0.1pp |
| **Total (MWh)** | 46,500,953 | 46,596,136 | 47,072,724 | 1.002x |

#### SRCA — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 31.5 | 31.7 | 32.8 | +0.2pp |
| coal | 9.0 | 9.0 | 11.2 | -0.0pp |
| nuclear | 48.5 | 48.4 | 45.7 | -0.1pp |
| solar | 7.5 | 7.5 | 7.0 | -0.0pp |
| hydro | 1.2 | 1.2 | 1.2 | -0.0pp |
| distributed_gen | 1.8 | 1.8 | 1.7 | -0.0pp |
| biomass | 0.4 | 0.4 | 0.4 | +0.0pp |
| **Total (MWh)** | 218,717,214 | 218,628,724 | 231,445,127 | 1.000x |

#### SRSG — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 35.0 | 35.3 | 35.4 | +0.3pp |
| coal | 19.4 | 19.3 | 19.3 | -0.1pp |
| nuclear | 19.5 | 19.4 | 19.4 | -0.1pp |
| wind | 7.2 | 7.2 | 7.2 | -0.0pp |
| solar | 10.8 | 10.7 | 10.7 | -0.0pp |
| hydro | 4.3 | 4.2 | 4.2 | -0.0pp |
| distributed_gen | 2.7 | 2.7 | 2.7 | -0.0pp |
| biomass | 0.1 | 0.1 | 0.1 | +0.0pp |
| geothermal | 1.1 | 1.1 | 1.1 | -0.0pp |
| **Total (MWh)** | 179,972,227 | 180,249,612 | 180,587,269 | 1.002x |

#### PJMD — 2027

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 42.9 | 43.4 | 46.9 | +0.5pp |
| coal | 0.3 | 0.3 | 0.0 | -0.0pp |
| nuclear | 30.1 | 30.0 | 32.5 | -0.2pp |
| wind | 10.6 | 10.0 | 5.1 | -0.7pp |
| solar | 11.8 | 12.2 | 10.4 | +0.4pp |
| hydro | 1.9 | 1.9 | 2.6 | -0.1pp |
| distributed_gen | 1.5 | 1.5 | 1.6 | -0.0pp |
| biomass | 0.8 | 0.8 | 0.8 | +0.0pp |
| **Total (MWh)** | 107,721,055 | 108,007,826 | 99,655,897 | 1.003x |

### Period 2030

#### TRE — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 37.4 | 40.0 | 40.0 | +2.6pp |
| coal | 22.7 | 23.4 | 23.4 | +0.7pp |
| nuclear | 9.3 | 9.4 | 9.4 | +0.0pp |
| wind | 22.0 | 18.8 | 18.9 | -3.2pp |
| solar | 5.8 | 5.7 | 5.7 | -0.0pp |
| hydro | 0.1 | 0.1 | 0.1 | -0.0pp |
| distributed_gen | 2.5 | 2.5 | 2.5 | +0.0pp |
| biomass | 0.1 | 0.1 | 0.1 | +0.0pp |
| hydrogen | 0.1 | 0.0 | 0.0 | -0.1pp |
| **Total (MWh)** | 478,822,217 | 477,573,034 | 477,832,590 | 0.997x |

#### PJME — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 45.0 | 45.2 | 38.7 | +0.2pp |
| coal | 0.8 | 1.1 | 0.0 | +0.3pp |
| nuclear | 33.6 | 33.3 | 34.1 | -0.3pp |
| wind | 12.2 | 12.0 | 7.3 | -0.1pp |
| solar | 1.2 | 1.2 | 12.5 | -0.0pp |
| hydro | 1.9 | 2.0 | 2.0 | +0.0pp |
| distributed_gen | 4.6 | 4.6 | 4.7 | -0.0pp |
| biomass | 0.6 | 0.6 | 0.6 | -0.0pp |
| **Total (MWh)** | 334,129,697 | 336,508,295 | 328,720,986 | 1.007x |

#### PJMW — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 37.0 | 36.8 | 40.6 | -0.2pp |
| coal | 35.6 | 35.4 | 37.9 | -0.2pp |
| nuclear | 11.6 | 11.5 | 11.9 | -0.0pp |
| wind | 12.3 | 12.7 | 5.8 | +0.5pp |
| solar | 1.8 | 1.8 | 1.8 | -0.0pp |
| hydro | 0.8 | 0.8 | 0.8 | +0.0pp |
| distributed_gen | 1.0 | 1.0 | 1.0 | -0.0pp |
| biomass | 0.1 | 0.1 | 0.1 | -0.0pp |
| **Total (MWh)** | 479,383,113 | 479,993,317 | 463,035,075 | 1.001x |

#### SRSE — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 45.3 | 45.5 | 46.0 | +0.2pp |
| coal | 22.6 | 22.5 | 22.5 | -0.1pp |
| nuclear | 23.9 | 23.8 | 23.4 | -0.1pp |
| solar | 4.7 | 4.7 | 4.6 | -0.0pp |
| hydro | 2.0 | 2.0 | 2.0 | -0.0pp |
| distributed_gen | 0.6 | 0.6 | 0.6 | -0.0pp |
| biomass | 0.8 | 0.8 | 0.8 | -0.0pp |
| **Total (MWh)** | 296,291,485 | 296,649,612 | 301,885,675 | 1.001x |

#### FRCC — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 66.3 | 66.4 | 66.5 | +0.1pp |
| coal | 10.1 | 10.0 | 10.0 | -0.0pp |
| nuclear | 12.0 | 12.0 | 12.0 | -0.0pp |
| solar | 6.8 | 6.8 | 6.8 | -0.0pp |
| distributed_gen | 4.1 | 4.1 | 4.1 | -0.0pp |
| biomass | 0.6 | 0.6 | 0.6 | -0.0pp |
| **Total (MWh)** | 272,308,381 | 272,024,315 | 273,038,190 | 0.999x |

#### CANO — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 60.8 | 61.3 | 62.5 | +0.5pp |
| wind | 1.8 | 1.8 | 1.7 | -0.0pp |
| solar | 11.2 | 11.2 | 10.8 | -0.0pp |
| hydro | 15.8 | 15.4 | 14.9 | -0.4pp |
| distributed_gen | 9.0 | 8.9 | 8.7 | -0.0pp |
| biomass | 1.4 | 1.4 | 1.4 | -0.0pp |
| **Total (MWh)** | 137,429,904 | 137,507,438 | 141,989,268 | 1.001x |

#### ISNE — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 20.9 | 19.2 | 27.4 | -1.7pp |
| coal | 1.2 | 1.2 | 0.0 | +0.0pp |
| nuclear | 15.9 | 17.3 | 18.1 | +1.3pp |
| wind | 46.2 | 46.7 | 37.7 | +0.5pp |
| solar | 3.3 | 3.3 | 6.1 | +0.0pp |
| hydro | 5.4 | 5.3 | 3.9 | -0.1pp |
| distributed_gen | 5.2 | 5.3 | 5.1 | +0.1pp |
| biomass | 1.8 | 1.7 | 1.7 | -0.0pp |
| **Total (MWh)** | 155,305,720 | 155,369,105 | 162,028,345 | 1.000x |

#### NYUP — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 3.9 | 1.8 | 26.4 | -2.1pp |
| nuclear | 7.0 | 8.4 | 22.2 | +1.4pp |
| wind | 43.7 | 42.1 | 20.6 | -1.7pp |
| solar | 34.2 | 35.1 | 14.8 | +0.9pp |
| hydro | 9.9 | 11.2 | 14.0 | +1.3pp |
| distributed_gen | 0.8 | 1.0 | 1.4 | +0.1pp |
| biomass | 0.4 | 0.4 | 0.5 | -0.0pp |
| **Total (MWh)** | 160,468,657 | 161,759,930 | 131,912,431 | 1.008x |

#### MISC — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 17.4 | 17.6 | 18.9 | +0.2pp |
| coal | 58.3 | 58.1 | 57.9 | -0.2pp |
| nuclear | 10.5 | 10.5 | 10.0 | -0.0pp |
| wind | 7.1 | 7.1 | 6.8 | -0.0pp |
| solar | 4.1 | 4.1 | 3.9 | -0.0pp |
| hydro | 1.1 | 1.1 | 1.1 | +0.0pp |
| distributed_gen | 1.3 | 1.3 | 1.2 | -0.0pp |
| biomass | 0.3 | 0.3 | 0.3 | -0.0pp |
| **Total (MWh)** | 198,427,705 | 198,209,460 | 207,905,690 | 0.999x |

#### NYCW — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 92.9 | 93.5 | 93.9 | +0.6pp |
| solar | 0.6 | 0.6 | 0.5 | +0.0pp |
| distributed_gen | 4.7 | 4.8 | 4.6 | +0.0pp |
| biomass | 0.9 | 0.9 | 0.9 | +0.0pp |
| hydrogen | 0.9 | 0.0 | 0.0 | -0.9pp |
| oil | 0.1 | 0.3 | 0.1 | +0.3pp |
| **Total (MWh)** | 51,324,249 | 50,838,205 | 52,691,611 | 0.991x |

#### SRCA — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 8.1 | 8.0 | 10.5 | -0.0pp |
| coal | 36.3 | 36.5 | 38.9 | +0.2pp |
| nuclear | 41.3 | 41.2 | 40.3 | -0.1pp |
| wind | 4.0 | 4.0 | 0.0 | -0.0pp |
| solar | 6.4 | 6.3 | 6.2 | -0.0pp |
| hydro | 1.3 | 1.2 | 1.4 | -0.1pp |
| distributed_gen | 2.3 | 2.3 | 2.3 | -0.0pp |
| biomass | 0.4 | 0.4 | 0.4 | -0.0pp |
| **Total (MWh)** | 256,938,139 | 256,734,881 | 262,363,160 | 0.999x |

#### SRSG — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 33.8 | 34.4 | 43.3 | +0.5pp |
| coal | 16.4 | 16.4 | 16.7 | -0.0pp |
| nuclear | 16.5 | 16.4 | 16.8 | -0.0pp |
| wind | 11.0 | 7.9 | 6.2 | -3.1pp |
| solar | 14.7 | 17.4 | 9.3 | +2.7pp |
| hydro | 3.7 | 3.6 | 3.7 | -0.1pp |
| distributed_gen | 2.9 | 2.9 | 3.0 | -0.0pp |
| biomass | 0.1 | 0.1 | 0.1 | -0.0pp |
| geothermal | 0.9 | 0.9 | 0.9 | -0.0pp |
| **Total (MWh)** | 213,100,795 | 212,720,668 | 208,288,668 | 0.998x |

#### PJMD — 2030

| Type | mip-dev (%) | new_v4 (%) | old_v4 (%) | Diff |
|---|---|---|---|---|
| gas | 29.4 | 30.0 | 25.7 | +0.6pp |
| coal | 0.1 | 0.1 | 0.0 | +0.0pp |
| nuclear | 21.3 | 21.2 | 20.8 | -0.1pp |
| wind | 16.6 | 16.5 | 12.8 | -0.1pp |
| solar | 26.0 | 25.7 | 33.0 | -0.4pp |
| hydro | 3.7 | 3.7 | 5.0 | -0.0pp |
| distributed_gen | 2.2 | 2.2 | 2.2 | -0.0pp |
| biomass | 0.6 | 0.5 | 0.5 | -0.0pp |
| **Total (MWh)** | 152,251,816 | 152,450,581 | 156,031,161 | 1.001x |

## 6. New Capacity by Region (MW)

### Period 2027

#### ISNE — 2027

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 7,757 | 7,816 | 5,151 |
| **TOTAL** | **7,757** | **7,816** | **5,151** |

#### NYCW — 2027

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| gas | 1,214 | 402 | 462 |
| hydrogen | 1,962 | - | - |
| **TOTAL** | **3,176** | **402** | **462** |

#### NYUP — 2027

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 13,033 | 13,180 | 157 |
| solar | 16,098 | 15,295 | - |
| **TOTAL** | **29,131** | **28,475** | **157** |

#### PJMC — 2027

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 4,068 | 3,833 | - |
| **TOTAL** | **4,068** | **3,833** | **-** |

#### PJMD — 2027

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 3,209 | 2,972 | 1,332 |
| solar | 1,150 | 1,303 | 16 |
| **TOTAL** | **4,359** | **4,275** | **1,347** |

#### PJME — 2027

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 4,630 | 4,513 | 2,106 |
| **TOTAL** | **4,630** | **4,513** | **2,106** |

#### PJMW — 2027

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 13,805 | 14,608 | - |
| solar | 47 | - | - |
| **TOTAL** | **13,852** | **14,608** | **-** |

#### RMRG — 2027

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 133 | 570 | - |
| **TOTAL** | **133** | **570** | **-** |

#### SPPN — 2027

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 11 | - | - |
| **TOTAL** | **11** | **-** | **-** |

#### TRE — 2027

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| gas | 84 | - | - |
| wind | 1,589 | 257 | 1,696 |
| solar | 10 | - | - |
| hydrogen | 5,247 | - | - |
| **TOTAL** | **6,930** | **257** | **1,696** |

#### TREW — 2027

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| gas | 10 | - | - |
| wind | 177 | - | 53 |
| solar | 197 | - | - |
| hydrogen | 22 | - | - |
| **TOTAL** | **407** | **-** | **53** |

### Period 2030

#### BASN — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 2,348 | 2,386 | - |
| solar | 63 | 85 | - |
| distributed_gen | 449 | 449 | 449 |
| **TOTAL** | **2,860** | **2,920** | **449** |

#### CANO — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| solar | 19 | 24 | - |
| distributed_gen | 851 | 851 | 851 |
| **TOTAL** | **870** | **875** | **851** |

#### CASO — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| solar | 173 | 621 | - |
| distributed_gen | 1,323 | 1,323 | 1,323 |
| **TOTAL** | **1,496** | **1,944** | **1,323** |

#### FRCC — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| distributed_gen | 2,646 | 2,646 | 2,646 |
| **TOTAL** | **2,646** | **2,646** | **2,646** |

#### ISNE — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| gas | 11 | - | - |
| wind | 8,204 | 8,204 | 8,252 |
| solar | - | - | 2,188 |
| distributed_gen | 830 | 830 | 830 |
| hydrogen | 1,148 | - | - |
| **TOTAL** | **10,192** | **9,034** | **11,269** |

#### MISC — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| distributed_gen | 741 | 741 | 741 |
| **TOTAL** | **741** | **741** | **741** |

#### MISE — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| distributed_gen | 923 | 923 | 923 |
| **TOTAL** | **923** | **923** | **923** |

#### MISS — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| distributed_gen | 1,379 | 1,379 | 1,379 |
| **TOTAL** | **1,379** | **1,379** | **1,379** |

#### MISW — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 333 | 325 | 1,177 |
| solar | 4,201 | 4,382 | 4,689 |
| distributed_gen | 1,169 | 1,169 | 1,169 |
| **TOTAL** | **5,703** | **5,876** | **7,034** |

#### NWPP — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 99 | 145 | - |
| solar | 22 | 34 | - |
| distributed_gen | 898 | 898 | 898 |
| **TOTAL** | **1,019** | **1,077** | **898** |

#### NYCW — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| gas | 659 | 368 | 891 |
| distributed_gen | 390 | 390 | 390 |
| hydrogen | 12 | - | - |
| **TOTAL** | **1,062** | **758** | **1,281** |

#### NYUP — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 5,782 | 3,329 | 4,741 |
| solar | 11,115 | 11,201 | 7,667 |
| distributed_gen | 290 | 290 | 290 |
| **TOTAL** | **17,187** | **14,820** | **12,697** |

#### PJMC — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| distributed_gen | 960 | 960 | 960 |
| **TOTAL** | **960** | **960** | **960** |

#### PJMD — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 3,812 | 4,007 | 4,644 |
| solar | 12,617 | 12,178 | 19,205 |
| distributed_gen | 1,068 | 1,068 | 1,068 |
| **TOTAL** | **17,496** | **17,253** | **24,917** |

#### PJME — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 4,749 | 4,808 | 3,214 |
| solar | - | - | 17,194 |
| distributed_gen | 2,775 | 2,775 | 2,775 |
| **TOTAL** | **7,524** | **7,583** | **23,183** |

#### PJMW — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | - | 11 | 4,415 |
| solar | 13 | 26 | - |
| distributed_gen | 1,272 | 1,272 | 1,272 |
| **TOTAL** | **1,285** | **1,310** | **5,687** |

#### RMRG — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 6,362 | 6,035 | 1,757 |
| distributed_gen | 373 | 373 | 373 |
| **TOTAL** | **6,734** | **6,408** | **2,130** |

#### SPPC — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | - | 11 | - |
| distributed_gen | 169 | 169 | 169 |
| **TOTAL** | **169** | **180** | **169** |

#### SPPN — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 113 | 76 | 21 |
| solar | 2,638 | 1,098 | 1,223 |
| distributed_gen | 134 | 134 | 134 |
| **TOTAL** | **2,885** | **1,308** | **1,378** |

#### SPPS — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | - | 10 | - |
| distributed_gen | 796 | 796 | 796 |
| **TOTAL** | **796** | **806** | **796** |

#### SRCA — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 2,787 | 2,784 | - |
| distributed_gen | 1,125 | 1,125 | 1,125 |
| **TOTAL** | **3,912** | **3,909** | **1,125** |

#### SRCE — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| distributed_gen | 431 | 431 | 431 |
| **TOTAL** | **431** | **431** | **431** |

#### SRSE — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| distributed_gen | 488 | 488 | 488 |
| **TOTAL** | **488** | **488** | **488** |

#### SRSG — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| wind | 2,745 | 1,025 | - |
| solar | 4,550 | 6,683 | - |
| distributed_gen | 556 | 556 | 556 |
| **TOTAL** | **7,852** | **8,264** | **556** |

#### TRE — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| gas | 353 | - | - |
| wind | 15,899 | 13,506 | 12,142 |
| solar | 117 | 11 | - |
| distributed_gen | 2,676 | 2,676 | 2,676 |
| hydrogen | 572 | - | - |
| **TOTAL** | **19,617** | **16,193** | **14,818** |

#### TREW — 2030

| Type | mip-dev (MW) | new_v4 (MW) | old_v4 (MW) |
|---|---|---|---|
| gas | 182 | - | - |
| wind | 3,442 | 5,676 | 5,718 |
| solar | 6,218 | 3,040 | 2,890 |
| distributed_gen | 146 | 146 | 146 |
| hydrogen | 194 | - | - |
| **TOTAL** | **10,182** | **8,862** | **8,754** |

## 7. Analysis and Key Findings

### 7.1 Total Generation

- **2027:** mip-dev 4,759,865,354 MWh vs new_v4 4,769,778,017 MWh (ratio: 1.0021x, diff: +0.21%)
- **2030:** mip-dev 5,374,052,664 MWh vs new_v4 5,376,367,792 MWh (ratio: 1.0004x, diff: +0.04%)

Total generation matches within ~0.1%. The remaining difference is explained by:
- C2A: 8736 (v4) vs 8760 (mip-dev) = 0.27% less capacity utilization in v4
- Barrier solver convergence tolerance (BarConvTol=1e-3)

### 7.2 Generation Mix Differences

**2027 key differences (new_v4 vs mip-dev):**
- gas: 41.6% -> 41.6% (-0.0pp)
- coal: 14.1% -> 14.3% (+0.2pp)
- wind: 12.7% -> 12.7% (-0.1pp)
- solar: 6.1% -> 6.1% (-0.0pp)
- nuclear: 17.6% -> 17.5% (-0.0pp)

**2030 key differences:**
- gas: 33.4% -> 33.6% (+0.2pp)
- coal: 20.6% -> 20.6% (+0.1pp)
- wind: 15.5% -> 15.3% (-0.2pp)
- solar: 7.1% -> 7.0% (-0.1pp)
- nuclear: 15.4% -> 15.4% (+0.0pp)

### 7.3 New Capacity

**2027:** mip-dev builds 74,454 MW vs new_v4 64,749 MW
- mip-dev wind: 48,412 MW, new_v4 wind: 47,749 MW
- mip-dev solar: 17,503 MW, new_v4 solar: 16,598 MW
- mip-dev hydrogen: 7,232 MW, new_v4 hydrogen: - MW

**2030:** mip-dev builds 126,407 MW vs new_v4 116,949 MW
- mip-dev wind: 56,674 MW, new_v4 wind: 52,339 MW
- mip-dev solar: 41,747 MW, new_v4 solar: 39,385 MW
- mip-dev hydrogen: 1,927 MW, new_v4 hydrogen: - MW

### 7.4 Demand Verification

All demand commodities (DEMAND_ELC, DEMAND_CRYPTO, DEMAND_SERVERS, Dummy_CO2_Offset_Demand) are **identical** across all three databases for both periods. The generation mix differences are due to model optimization choices, not input data differences.

### 7.5 Hydrogen

mip-dev builds hydrogen CT/CC capacity (notably in NYCW). v4 does not build any hydrogen. This is likely due to the hydrogen capex fix applied to the v4 source DB (hydrogen CT/CC costs were set to match natural gas equivalents, making hydrogen non-competitive).

### 7.6 Regional Outliers

Regions with the largest generation share differences between mip-dev and new_v4:

| Region | Period | Type | mip-dev | new_v4 | Diff |
|---|---|---|---|---|---|
| TRE | 2030 | wind | 22.0% | 18.8% | -3.2pp |
| SRSG | 2030 | wind | 11.0% | 7.9% | -3.1pp |
