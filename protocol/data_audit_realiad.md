# Data audit

Objects: 30210  |  overall pass: **False**

## Blocking checks

| Check | Violations |
| --- | --- |
| wrong_view_count | 0 |
| duplicate_view_ids | 0 |
| label_vs_view_or_mismatch | 1 |
| objects_with_missing_image | 0 |

## Non-blocking

| Check | Count |
| --- | --- |
| objects_with_missing_mask | 0 |
| mask_size_mismatch | 0 |
| duplicate_content_hash | 0 |

## Annotation status

| Status | Count |
| --- | --- |
| empty_mask_on_anomaly | 1 |
| ok | 30209 |

## Per category

| Category | objects | normal | anomalous | mean k | P(k<=2) | median defect area | thin strata |
| --- | --- | --- | --- | --- | --- | --- | --- |
| regulator | 1020 | 498 | 522 | 2.069 | 0.8544 | 0.00073 | 4 |
| woodstick | 1001 | 501 | 500 | 2.14 | 0.756 | 0.002066 | 3,4 |
| plastic_nut | 1002 | 502 | 500 | 2.48 | 0.724 | 0.001155 | - |
| u_block | 998 | 499 | 499 | 2.417 | 0.6854 | 0.001843 | - |
| fire_hood | 1005 | 501 | 504 | 2.679 | 0.6508 | 0.000937 | 3,4 |
| porcelain_doll | 1000 | 483 | 517 | 2.427 | 0.6054 | 0.001138 | - |
| audiojack | 1010 | 493 | 517 | 2.507 | 0.5957 | 0.001785 | - |
| tape | 1020 | 500 | 520 | 2.775 | 0.5635 | 0.002057 | - |
| mounts | 1010 | 499 | 511 | 2.616 | 0.5616 | 0.002234 | 4 |
| eraser | 1013 | 492 | 521 | 2.85 | 0.5374 | 0.001769 | - |
| vcpill | 1005 | 504 | 501 | 2.934 | 0.5269 | 0.005295 | - |
| usb_adaptor | 1003 | 461 | 542 | 2.801 | 0.4945 | 0.000583 | - |
| toy_brick | 1002 | 496 | 506 | 3.036 | 0.4941 | 0.001847 | - |
| bottle_cap | 1003 | 492 | 511 | 3.188 | 0.4912 | 0.00058 | - |
| plastic_plug | 999 | 485 | 514 | 2.761 | 0.4397 | 0.000843 | - |
| mint | 1061 | 334 | 727 | 2.884 | 0.4374 | 0.000429 | - |
| phone_battery | 1000 | 483 | 517 | 2.996 | 0.4352 | 0.001616 | - |
| usb | 1010 | 492 | 518 | 3.386 | 0.3591 | 0.001301 | - |
| wooden_beads | 1001 | 435 | 566 | 2.975 | 0.3587 | 0.001572 | - |
| terminalblock | 1010 | 487 | 523 | 3.834 | 0.2447 | 0.00098 | - |
| button_battery | 1000 | 483 | 517 | 4.157 | 0.205 | 0.001639 | - |
| sim_card_set | 1006 | 498 | 508 | 4.071 | 0.2047 | 0.001536 | 2,3 |
| toothbrush | 1001 | 489 | 512 | 3.959 | 0.1914 | 0.006989 | - |
| end_cap | 1002 | 482 | 520 | 4.198 | 0.1769 | 0.001006 | - |
| pcb | 1002 | 493 | 509 | 4.497 | 0.1002 | 0.001188 | - |
| switch | 1010 | 492 | 518 | 3.849 | 0.0579 | 0.002003 | - |
| transistor1 | 1000 | 497 | 503 | 4.207 | 0.0577 | 0.002459 | 2 |
| rolled_strip_base | 1010 | 497 | 513 | 4.922 | 0.0058 | 0.001977 | 1,3 |
| toy | 1005 | 499 | 506 | 4.328 | 0.004 | 0.000935 | 2 |
| zipper | 1001 | 501 | 500 | 4.662 | 0.0 | 0.005804 | - |
