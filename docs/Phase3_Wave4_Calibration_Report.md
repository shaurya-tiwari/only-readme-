# Phase 3 Wave 4 Calibration Report

This report uses the enlarged local working-repo decision-memory dataset after Wave 4 calibration setup.

## Current Snapshot

- logged claim-created rows: `347`
- resolved labels: `81`
- false reviews: `44`
- replay rows: `347`
- replay match rate: `83.3%`

## False Review Score Bands

```text
False reviews by score band

0.60_0.65    ####################          31 ( 70.5%)
0.45_0.55    #####                          8 ( 18.2%)
ge_0.65      ###                            5 ( 11.4%)
```

## False Review Payout Bands

```text
False reviews by payout band

lt_75        #################             27 ( 61.4%)
75_125       ###########                   17 ( 38.6%)
```

## Replay Transition Summary

```text
Stored decision -> current policy replay

approved->approved #################            205 ( 59.1%)
delayed->delayed #####                         67 ( 19.3%)
delayed->approved ###                           34 (  9.8%)
rejected->rejected #                             17 (  4.9%)
rejected->delayed #                             12 (  3.5%)
approved->delayed #                             10 (  2.9%)
approved->rejected #                              1 (  0.3%)
delayed->rejected #                              1 (  0.3%)
```

## Dominant False Review Patterns

- flags: `movement, pre_activity`
  count: `18` share: `40.9%`
- flags: `cluster, device`
  count: `9` share: `20.5%`
- flags: `device`
  count: `8` share: `18.2%`
- flags: `cluster, pre_activity`
  count: `4` share: `9.1%`
- flags: `device, movement, pre_activity`
  count: `2` share: `4.5%`

## Replay Lift

- delayed -> approved: `34`
- approved -> delayed: `10`
- rejected -> approved: `0`

## Takeaway

The biggest waste is still the `0.60-0.65` band. The current policy already replays some old delayed claims as approved, but the enlarged dataset also shows stronger low-payout patterns such as `cluster + device`, so future loosening must stay narrow and evidence-based.