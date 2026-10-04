# Routing Logic

Implemented in `python/territory_router.py::route_account`. Rules run **in order**; the first match decides the status.

```
START
 |
 |-- Is_Duplicate = 1 ? ------------------------> Manual Review  (Duplicate Account)
 |
 |-- Country blank / not an APJ country ? ------> Ambiguous      (Missing Country | Invalid Country)
 |
 |-- Country = India AND Employee_Count blank ? > Manual Review  (Missing Employee Count)
 |
 |-- Account_Owner blank OR Sales_Territory blank ? -> Unassigned (No Owner | No Territory | both)
 |
 |-- Sales_Territory not a valid territory ? ---> Incorrectly Routed (Invalid Territory Value)
 |-- Sales_Territory != Expected_Territory ? ---> Incorrectly Routed (Territory Mismatch)
 |-- Account_Owner   != Expected_Owner ? -------> Incorrectly Routed (Owner Mismatch)
 |
 '-- otherwise ---------------------------------> Correctly Routed
```

## Calculated fields

| Field | Logic |
|---|---|
| Expected_Territory | `territory_mapping[Country].Territory`, else `Unknown` |
| Expected_Tier | Enterprise >= 5,000; Mid-Market 500-4,999; SMB < 500; else `Unknown` |
| Expected_Owner | Owner column for the tier from `territory_mapping`; null if India and tier unknown |
| Is_Covered | Owner present **and** Sales_Territory is one of the five valid territories |

## Metrics

* **Routable accounts** = Correctly Routed + Incorrectly Routed + Unassigned. Ambiguous and Manual Review are excluded because no deterministic expected route exists for them.
* **Routing Accuracy %** = Correctly Routed / Routable accounts.
* **Territory Coverage %** = Is_Covered / all accounts (by territory: grouped on Expected_Territory).
* **Open Exceptions** = every account whose status is not Correctly Routed (ambiguous, manual-review and duplicates included).

## Why this order?

Duplicates are removed from consideration first so that a copy is never "assigned" independently of its master. Country is next
because nothing downstream is knowable without it. India's tier check precedes the owner check because India is the only split-ownership
territory. Mismatch rules run last so that an unassigned account is reported as *unassigned*, not as a mismatch.

## Known limitations

* A territory edit and an owner edit are treated independently; if both are wrong the status shows the first problem found (territory).
* Duplicate detection needs a valid domain or a country + normalised name match; duplicates that lost both are not caught (3 of the 100 injected duplicates in the delivered dataset).
